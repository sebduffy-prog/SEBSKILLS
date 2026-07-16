---
name: mixture-of-models-ensemble
category: model-routing
description: >
  Fan one prompt to several models from different vendors in parallel, then have an aggregator model synthesize
  their drafts into one better answer (Together's Mixture-of-Agents / MoA pattern) — or the lighter draft-with-A,
  refine-with-B variant. Use when someone asks to "ensemble LLMs", "combine model outputs", "mixture of agents",
  "MoA", "poll multiple models and merge", "get a second opinion then synthesize", or wants higher answer quality
  by blending diverse models instead of trusting one. Ships a runnable multi-vendor moa.py.
when_to_use:
  - "I want to send the same prompt to GPT, Claude and a Llama model and merge the best answer"
  - "Set up a mixture-of-agents / MoA pipeline for higher-quality answers"
  - "Have one model draft and another critique-and-refine it"
  - "Ensemble several LLMs and aggregate their outputs into one response"
  - "Quality matters more than latency/cost — blend diverse models for a hard question"
when_not_to_use:
  - "Pick ONE cheapest-capable model per request → model-triage-router"
  - "Try cheap first, escalate to bigger only on failure → model-cascade-escalation"
  - "Score/rank candidate answers with a judge (no synthesis) → cross-vendor-llm-judge"
  - "One unified SDK/endpoint to reach many providers → cross-provider-gateway"
  - "Route different pipeline STEPS to different best models → best-model-per-step-pipeline"
keywords: [mixture of agents, moa, ensemble, model ensemble, aggregator, proposer, synthesize, multi-model, draft-refine, together, fan-out, blend models, second opinion, cross-vendor, llm ensemble]
similar_to: [cross-vendor-llm-judge, model-cascade-escalation, best-model-per-step-pipeline, cross-provider-gateway, model-triage-router]
inputs_needed:
  - Which proposer models + which single aggregator (and their API keys/endpoints)
  - The user prompt/task, and whether latency or answer quality dominates
  - Optional layer count (single-layer MoA is the strong default)
produces: A runnable MoA ensemble (scripts/moa.py) that fans a prompt to N vendors and returns one synthesized answer
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Mixture-of-Models Ensemble (MoA)

Fan one prompt to several **proposer** models (ideally from different vendors, for diversity), collect their
drafts, then hand all drafts to one **aggregator** model that critically synthesizes a single, better answer.
This is Together's Mixture-of-Agents; on AlpacaEval 2.0 a MoA of open models scored **65.1% vs GPT-4o's 57.5%**.
Trades latency + token cost for quality — use it on hard, high-value questions, not chat turns.

## When to use

- Correctness/quality matters more than latency or cost (analysis, code review, reasoning, drafting).
- You have API access to ≥2 capable models and want their diversity to cancel out individual blind spots.
- You want a principled "second opinion then merge", not just a vote or a judge score.

If you only need to *pick* one model, or *escalate* on failure, or *score* candidates — use the sibling skills
listed in the frontmatter instead. MoA specifically **synthesizes** a new answer.

## Prerequisites

- `pip install 'openai>=1.0'` — the OpenAI SDK talks to any OpenAI-compatible endpoint (OpenAI, Together,
  Fireworks, Groq, vLLM, OpenRouter) by swapping `base_url` + key. Anthropic needs its own SDK (see Pitfalls).
- API keys as env vars, e.g. `OPENAI_API_KEY`, `TOGETHER_API_KEY`. Together models use base URL
  `https://api.together.xyz/v1`; get a key at api.together.ai.
- Real cost/latency: N proposer calls run **in parallel** (~1 model of latency) + 1 aggregator call.
  Token spend ≈ N drafts + (prompt + all drafts) for the aggregator. Budget accordingly.

## Recipes

### Recipe 1 — Single-layer MoA (the strong default)

`scripts/moa.py` is ready to run. Edit `DEFAULT_PROPOSERS` / `DEFAULT_AGGREGATOR` to your models, then:

```bash
export OPENAI_API_KEY=sk-...
export TOGETHER_API_KEY=...
python3 scripts/moa.py "Design an idempotent webhook consumer. List failure modes." --show-drafts
```

The core loop (see the script for the full, error-handled version):

```python
# 1. Fan out to proposers in parallel
with ThreadPoolExecutor(max_workers=len(proposers)) as ex:
    refs = [f.result() for f in as_completed([ex.submit(ask, p, msgs) for p in proposers])]

# 2. Inject drafts as a numbered reference list into the aggregator's SYSTEM message (MoA-style)
system = AGGREGATOR_SYSTEM
for i, ref in enumerate(refs):
    system += f"\n{i+1}. {ref}"
final = ask(aggregator, [{"role":"system","content":system},
                         {"role":"user","content":prompt}], temperature=0.3)
```

The **verbatim MoA aggregator prompt** (ported from togethercomputer/MoA, Apache-2.0):

> You have been provided with a set of responses from various open-source models to the latest user query.
> Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically
> evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect.
> Your response should not simply replicate the given answers but should offer a refined, accurate, and
> comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the
> highest standards of accuracy and reliability.
>
> Responses from models:

Then a numbered list `1. <draft>`, `2. <draft>`, … is appended. Keep the aggregator temperature low (~0.3) — it
should reconcile, not improvise. Pick diverse proposers (different families/vendors); redundant models add cost
without adding signal.

### Recipe 2 — Multi-layer MoA (deeper, more expensive)

Feed the aggregated output back as fresh reference material for another proposer round, then aggregate again.
2–3 layers is the practical ceiling; each layer multiplies cost and latency for diminishing returns.

```python
proposals = prompt
for _ in range(n_layers):                       # each layer re-proposes then aggregates
    drafts = fan_out(proposers, proposals)      # proposers see prior layer's synthesis
    proposals = aggregate(aggregator, prompt, drafts)
final = proposals
```

### Recipe 3 — Draft-with-A, refine-with-B (the cheap 2-model variant)

When a full fan-out is overkill, just chain two models: a strong drafter, then a different reviewer that
critiques and rewrites. One extra call, big quality lift, minimal complexity.

```python
draft  = ask(model_a, [{"role":"user","content":prompt}])
final  = ask(model_b, [
    {"role":"system","content":"You are a rigorous reviewer. Improve the draft below: fix errors, "
        "tighten reasoning, keep what's correct. Return only the improved answer."},
    {"role":"user","content":f"Task:\n{prompt}\n\nDraft to improve:\n{draft}"}])
```

## Verify

- `python3 -c "import ast; ast.parse(open('scripts/moa.py').read())"` — syntax check (no key needed).
- Run with `--show-drafts` and confirm on stderr that each proposer returned a *distinct* draft and the final
  answer is not a verbatim copy of any single one (that's the synthesis working).
- Kill one proposer's key and re-run: the ensemble should warn and still aggregate the survivors, not crash.
- A/B it: compare the MoA answer vs your best single model on 5–10 hard prompts. If MoA doesn't win, your
  proposers aren't diverse enough or the task is too easy to justify the cost — drop back to a single model.

## Pitfalls

- **Latency & cost are real.** N proposers + 1 aggregator per query. Reserve MoA for high-value questions;
  route everyday turns through model-triage-router.
- **Diversity beats count.** Three near-identical models ≈ one model at 3× cost. Mix vendors/families.
- **Aggregator dominates quality.** Use your *strongest* model as aggregator, low temperature. A weak
  aggregator can launder a good draft into a worse blend.
- **Anthropic isn't OpenAI-compatible on the raw endpoint.** Wrap Claude proposers with `anthropic` SDK (or
  route through OpenRouter's OpenAI-compatible endpoint) and adapt the `ask()` function.
- **Long-draft context blowup.** Many verbose proposers can overflow the aggregator's context; cap proposer
  `max_tokens` and consider summarizing drafts before injection.
- **One dead proposer must not sink the run.** The script catches per-proposer failures and aggregates
  whatever survived — keep that behavior if you rewrite it.
- **Not a judge.** MoA merges; it does not rank or gate. If you need a pass/fail verdict or scoring, use
  cross-vendor-llm-judge.

## Attribution

MoA architecture and the aggregator prompt are ported from **togethercomputer/MoA** (Apache-2.0). Full license
in `LICENSE` beside this skill. Paper: *Mixture-of-Agents Enhances Large Language Model Capabilities* (Wang et
al., 2024).
