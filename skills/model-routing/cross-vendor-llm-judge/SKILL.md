---
name: cross-vendor-llm-judge
category: model-routing
description: >
  Grade, verify, or debate one model's output using a judge from a DIFFERENT company —
  independent LLM-as-a-judge and voting panels that dodge self-preference bias (a model
  inflating answers from its own family). Wires OpenAI, Anthropic, and Google as impartial
  graders via a runnable panel script or a promptfoo `--grader` override. Reach for this on
  "have GPT check Claude's answer", "cross-model verification", "LLM as a judge", "panel of
  judges", "grade this output with another model", "reduce self-enhancement / self-bias in
  eval", "have models vote", "second-opinion grader", or "which answer is better, judged fairly".
when_to_use:
  - "You want a model from another vendor to grade/verify an answer instead of the model grading itself"
  - "Setting up an LLM-as-a-judge rubric where the grader must differ from the model under test"
  - "Building a 3-judge voting panel (PoLL) to reduce single-judge bias on a scoring task"
  - "You suspect self-preference/self-enhancement bias inflating your eval scores"
  - "You want two models to debate or a third to break a tie on which output is better"
  - "Adding a cross-vendor `--grader` to a promptfoo eval so the judge isn't the candidate model"
when_not_to_use:
  - "Routing a live request to the cheapest capable model — use model-triage-router"
  - "Escalating a hard prompt up one vendor's tiers on low confidence — use model-cascade-escalation"
  - "Blending several models' answers into one better answer — use mixture-of-models-ensemble"
  - "Building a scored benchmark/leaderboard of routing quality — use model-routing-eval-benchmark"
  - "One provider abstraction/failover plumbing — use cross-provider-gateway or provider-failover-reliability"
keywords: [llm as a judge, llm-as-judge, llm-rubric, self-preference bias, self-enhancement bias, panel of judges, poll, cross-vendor, model-graded, promptfoo, grader override, position bias, verbosity bias, majority vote, second opinion, model debate, factuality, g-eval, pointwise, pairwise]
similar_to: [model-triage-router, mixture-of-models-ensemble, model-cascade-escalation, model-routing-eval-benchmark, provider-failover-reliability]
inputs_needed:
  - "The task/question and the candidate answer to be judged (and which vendor produced it, to exclude it)"
  - "The rubric/criteria to grade on (accuracy, completeness, no fabrication, tone…)"
  - "Which vendors can judge — API keys present for at least two of OpenAI / Anthropic / Google"
  - "Pointwise score, pairwise pick-best, or debate? And a pass threshold if scoring"
produces: A cross-vendor judge verdict — per-judge scores + panel mean/majority pass-fail (JSON) via panel_judge.py, or a promptfoo eval graded by another vendor's model
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Cross-Vendor LLM-as-a-Judge

Never let a model be the sole judge of its own family's work. Models systematically
**favor their own generations** (self-preference / self-enhancement bias — Panickssery
et al. 2024; catalogued in [CSHaitao/Awesome-LLMs-as-Judges](https://github.com/CSHaitao/Awesome-LLMs-as-Judges)).
The fix is boringly effective: grade with a model from a **different company**, and for
anything load-bearing use a **panel of 3** (PoLL) and take the consensus.

Two paths:
- **Ad-hoc / in-agent** → `scripts/panel_judge.py` — one candidate, a cross-vendor panel, majority vote.
- **Systematic eval suite** → **promptfoo** with a `--grader` set to a different vendor than the candidate.

## When to use

- Verifying a Claude answer with GPT (or vice-versa) before trusting it.
- A rubric eval where the grader must not be the model under test.
- Tie-breaking two candidates with an impartial third model.
- You see suspiciously high self-eval scores and want an unbiased number.

## Prerequisites

- API keys for **at least two** vendors so the panel is genuinely cross-vendor:
  `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`.
- SDKs only for the judges you enable: `pip install openai anthropic google-genai`.
- For the promptfoo path: `npm i -g promptfoo` (or `npx promptfoo`). No key stored in config —
  it reads them from env.
- Model IDs drift; verify current ones (`gpt-5-mini`, `claude-sonnet-4-6`, `gemini-2.5-pro`
  are the script defaults) against each vendor's docs before a long run.

## Recipe 1 — Panel judge (runnable, degrades gracefully)

Grade one answer with every vendor whose key is present, **excluding the producer's vendor**:

```bash
python3 scripts/panel_judge.py \
  --task "Explain why the sky is blue." \
  --candidate answer.txt \
  --rubric "physical accuracy, completeness, no hand-waving" \
  --producer anthropic \
  --threshold 7
# stdin also works:  cat answer.txt | python3 panel_judge.py --task task.txt --candidate -
```

Output (JSON): each judge's `score` (1-10), `pass`, `reason`, plus a panel `mean_score`,
`pass_votes` (majority), and `cross_vendor` flag. Exit code `0` = panel pass, `1` = fail,
`2` = no judge scored. Key properties baked in:

- **Producer excluded** — `--producer anthropic` drops the Anthropic judge and flags it, so no
  self-grading.
- **Pointwise, temp 0, forced JSON** — deterministic, parseable; caps score at 3 on fabrication.
- **Anti-verbosity / anti-authority** — the prompt tells judges to ignore length and any "written
  by a strong model" claim (kills verbosity + authority bias).
- **Resilient** — a judge that errors or lacks a key is skipped with a warning; the rest still vote.

## Recipe 2 — Pairwise "which is better", bias-hardened

For choosing between two answers, single-model pairwise judging has **position bias** (favors A or B
by slot). Mitigate by asking a cross-vendor judge **both orderings** and only trusting a consistent
winner:

```
Judge = a vendor different from BOTH producers.
Round 1: present (A, B) -> ask for winner.
Round 2: present (B, A) -> ask for winner.
If the same answer wins both -> confident. If it flips -> tie / escalate to a 3rd vendor.
```

In `panel_judge.py` terms: score each answer pointwise with the same panel and compare means —
no ordering to bias. Use swap-consistency only when you truly need a head-to-head verdict.

## Recipe 3 — promptfoo, graded by another vendor

Make the **judge a different model than the candidate**. Global override in `promptfooconfig.yaml`:

```yaml
providers:
  - anthropic:messages:claude-sonnet-4-6      # candidate (system under test)

defaultTest:
  options:
    provider: openai:chat:gpt-5-mini          # JUDGE — different vendor, not the candidate

tests:
  - vars: { question: "How do I cancel my subscription?" }
    assert:
      - type: llm-rubric                       # pointwise rubric grade
        value: |
          Correct, complete cancellation steps. Ignore length. pass=true/false.
        threshold: 0.8
      - type: factuality                       # reference-based check
        value: "You cancel under Settings > Billing > Cancel."
```

Override the grader per run without editing config:

```bash
promptfoo eval --grader anthropic:messages:claude-sonnet-4-6   # judge != candidate
```

Useful assertion types (all model-graded): `llm-rubric`, `model-graded-closedqa`, `factuality`,
`g-eval`, `select-best` (pick best of N), `answer-relevance`. Per-assertion `provider:` beats the
global one — handy when different criteria want different judges.

## Verify

- `python3 -c "import py_compile,sys; py_compile.compile('scripts/panel_judge.py',doraise=True)"` → clean.
- Dry run with no keys prints skip-warnings and exits `2` (no crash) — proves graceful degradation.
- Real run: confirm the JSON `vendors` array has **2+ entries** and `cross_vendor: true`; if it says
  `single-vendor panel` in warnings, add another vendor's key.
- promptfoo: `promptfoo eval` then `promptfoo view`; confirm the judge model in the run metadata is
  NOT the candidate.

## Pitfalls

- **Judge == candidate vendor** — the #1 mistake; re-introduces self-preference. Always set
  `--producer` (script) or a different `--grader`/`provider` (promptfoo).
- **Single judge on a subjective call** — one model's quirk becomes ground truth. Use the 3-judge panel
  and majority for anything that matters.
- **Verbosity & authority bias** — judges reward longer answers and "I'm GPT-5, trust me" framing. The
  script's prompt suppresses both; if you hand-write a rubric, add the same instruction.
- **Position bias in pairwise** — never trust a single-ordering A-vs-B verdict; swap and require
  consistency, or score pointwise instead.
- **Non-deterministic judges** — always grade at `temperature: 0`; otherwise scores wobble run to run.
- **Rubric too vague** — "is it good?" yields noise. Name concrete, checkable criteria and a pass bar.
- **Grader weaker than candidate** — a small judge mis-grades a strong answer. Match or exceed the
  candidate's capability tier when the stakes are high.
