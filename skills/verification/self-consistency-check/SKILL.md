---
name: self-consistency-check
category: verification
description: >
  Catch likely LLM hallucinations with NO knowledge base — re-sample the same answer N times at
  high temperature and flag any fact that changes across samples. Grounded, well-supported facts
  stay stable; fabricated ones drift (names, dates, numbers, citations wobble). Use on model output
  you can't fact-check because there's no source to check against — a bio, a "what is X" explainer,
  a list of studies, an API you're unsure exists. Ports the SelfCheckGPT sampling method into a
  runnable prompt loop. Outputs a per-sentence consistency score and a ranked risk list.
when_to_use:
  - You have LLM-generated text with no ground-truth source to verify it against (offline / zero-resource)
  - Output contains checkable atoms — names, dates, stats, citations, API signatures — that could be fabricated
  - You want a fast triage of WHICH sentences are risky before spending effort on real fact-checking
  - Screening a batch of generations (bios, summaries, FAQs) for hallucination-prone lines
  - You can re-query the same model that produced the text (temperature control available)
when_not_to_use:
  - You HAVE authoritative sources to check against — use claim-verifier (actually verifies truth)
  - The claim cites specific sources and you must confirm the quote/link matches — use citation-integrity-check
  - A single statistic's math or methodology is the concern — use stat-check-review
  - You want to grade how trustworthy the sources are — use source-credibility-audit
  - The text is human-written or you cannot re-query the generating model (no resampling possible)
keywords: [selfcheckgpt, hallucination, self-consistency, resampling, sampling, temperature, consistency score, nli, zero-resource, fact drift, llm output, verification, confabulation, triage]
similar_to: [claim-verifier, citation-integrity-check, stat-check-review, adversarial-argument-review, source-credibility-audit, research-methodology-review]
inputs_needed: The LLM output to check (a passage or list) and the original prompt/question that produced it. Ability to re-query the same (or a comparable) model. No API keys or knowledge base required.
produces: A per-sentence consistency score 0.0-1.0 (higher = more likely hallucinated), a ranked risk list of the least-consistent atoms, and a suggested next action (accept / re-fact-check / drop) per line.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Self-Consistency Check (SelfCheckGPT)

Detect probable hallucinations **without any external knowledge base**. The premise, from
Manakul et al.'s SelfCheckGPT (EMNLP 2023): when an LLM *knows* a fact, it reproduces it
consistently across independent stochastic samples; when it *fabricates*, the fabrication
varies — names swap, dates shift, statistics wander, cited papers change. So you re-sample the
same answer several times and measure how much each sentence agrees with the alternatives. Low
agreement = high hallucination risk. It flags *risk*, it does not prove truth.

## When to use

Reach for this when you have model output and **nothing to check it against** — the zero-resource
case where claim-verifier and citation-integrity-check can't run because there is no source. It
answers "which of these sentences should I distrust?" so you can spend real fact-checking effort
only on the risky ones. Classic targets: a generated bio, a "top 5 studies on X" list, a confident
explanation of an obscure API, a historical summary.

## Prerequisites

- **No API keys, no knowledge base, no downloads required** for the primary (prompt-based) recipe.
  You (the agent) act as the sampler and the consistency judge.
- **Ability to re-query the generating model** — you need N independent samples of the *same*
  question at a decorrelating temperature. In Claude Code you get this by re-answering the original
  prompt yourself N times, or by fanning out subagents.
- Optional heavy path: the `selfcheckgpt` PyPI package (NLI/BERTScore variants) needs PyTorch +
  transformers and a GPU is strongly preferred. On this Mac (python3.9, no brew) treat it as
  out-of-scope; use the prompt recipe below.

## Recipe A — Prompt-based self-check (primary, runnable now)

This is the SelfCheck-**Prompt** variant, the best performer in the paper (93.4 AUC-PR with
GPT-3.5). Five steps.

**1. Split the target into atomic sentences.** One checkable claim per line. Break compound
sentences ("Founded in 1998 by Larry Page and Sergey Brin" → founding year / founders separately)
so the score localises to the wobbling atom.

**2. Draw N stochastic samples of the whole answer.** Re-ask the *original question* (not "rephrase
the text above" — that copies the fabrication) N times, independently, at high temperature.
- Recommended: **N = 3 to 5** samples (paper uses up to 20; 3–5 is the practical triage sweet spot).
- Temperature ≈ **1.0** so samples decorrelate. Do not reuse the passage as context.
- In Claude Code: spawn N subagents (or N separate calls) each given only the original prompt.
  Keep the samples in variables `sample_1 … sample_N`; do not let them see each other.

**3. Score each sentence against each sample.** For sentence `s` and sample passage `c`, ask the
judge model the SelfCheckGPT prompt verbatim:

```
Context: {sample_passage}

Sentence: {sentence}

Is the sentence supported by the context above? Answer Yes or No.

Answer:
```

Map the answer to a number: **Yes → 0.0, No → 1.0, N/A/unclear → 0.5**.

**4. Average across samples** to get the sentence's inconsistency score:

```
score(s) = mean over the N samples of map(answer)
# 0.0 = every sample supports it (safe) … 1.0 = no sample supports it (likely hallucinated)
```

**5. Rank and act.** Sort sentences by score, descending. Suggested bands (tune to appetite):

| score | reading | action |
|-------|---------|--------|
| 0.0–0.2 | consistently reproduced | accept |
| 0.3–0.5 | partial drift | re-fact-check against a real source |
| 0.6–1.0 | fabrication-shaped | drop or verify before use — do not ship as-is |

Report a table: sentence · score · which atom moved across samples (e.g. "year was 1998 / 2004 /
1997"). The *disagreement itself* is the evidence — quote the conflicting values.

## Recipe B — N-gram / overlap fallback (no judge calls)

Cheaper, coarser triage when you can't afford N×M judge prompts. After drawing the N samples,
flag any **named entity, number, or date** in the target that appears in fewer than half the
samples. This mirrors SelfCheck-Ngram: tokens the model can't consistently regenerate are the
suspect ones. Good for a first pass over a long list; less precise than Recipe A.

## Optional heavy path — the real package

Only if you have a CUDA box, not this Mac:

```bash
pip install selfcheckgpt   # pulls torch + transformers; GPU strongly recommended
```

```python
from selfcheckgpt.modeling_selfcheck import SelfCheckNLI
selfcheck = SelfCheckNLI(device="cuda")           # DeBERTa-v3-large MNLI
scores = selfcheck.predict(
    sentences=sentences,                          # target, split into sentences
    sampled_passages=[sample_1, sample_2, sample_3],
)                                                 # → per-sentence P(contradiction), higher = worse
```

`SelfCheckNLI` (contradiction probability) is the paper's best non-prompt variant; other classes:
`SelfCheckBERTScore`, `SelfCheckMQAG`, `SelfCheckNgram`, `SelfCheckLLMPrompt`, `SelfCheckAPIPrompt`.

## Verify

Sanity-check the check itself before trusting scores:

- **Positive control:** insert one obviously-true, well-known sentence ("Water boils at 100°C at
  sea level"). It should score near 0.0. If it scores high, your samples aren't decorrelated or the
  judge prompt is misfiring.
- **Negative control:** insert one fabricated detail (a made-up citation). It should score high. If
  not, raise N or the temperature.
- **Independence:** confirm the N samples were generated *without* seeing the target or each other —
  shared context collapses the signal to zero.

## Pitfalls

- **Consistency ≠ truth.** A model can be confidently, consistently *wrong* (a widely-repeated myth
  scores 0.0). This is a hallucination *smoke detector*, not a fact-checker — escalate low-consistency
  lines to claim-verifier; it will not catch confident falsehoods. Say so in your report.
- **Low temperature kills the signal.** At temp 0 all samples are identical and every score is 0.0.
  You must sample at ≈1.0. This is the #1 mistake.
- **Re-summarising instead of re-asking.** If you generate samples by paraphrasing the target, you
  propagate the fabrication into every sample and it looks consistent. Always re-answer the *original
  question* from scratch.
- **Too few atoms.** Scoring whole paragraphs blurs one bad fact into three good ones. Split finely.
- **Subjective / opinion sentences** ("this is the best approach") have no truth value — exclude them
  or expect noisy scores; the method assumes checkable facts.
- **N too small.** N=1 is meaningless; N=2 is fragile. Use ≥3, more for high-stakes output.
- **Judge/generator collusion.** Using the exact same model as both sampler and judge can share a
  blind spot. Where it matters, judge with a different model than generated the samples.
