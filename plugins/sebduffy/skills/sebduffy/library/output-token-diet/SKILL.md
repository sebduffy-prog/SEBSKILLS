---
name: output-token-diet
category: model-routing
description: >
  Cut OUTPUT tokens 40-70% — the side you're billed 4-5x more for — without
  losing information, by combining chain-of-draft reasoning, structured/JSON
  output, tight max_tokens + stop_sequences caps, terse-response prompting,
  capped thinking budgets, and Claude 4+ token-efficient tool use. Use when
  someone says "my completion bill is too high", "responses are too verbose",
  "cut output tokens", "the model rambles", "reduce generation cost", "shrink
  the reasoning", "make it answer tersely", "stop the preamble", "the JSON has
  too much padding", or "output tokens dominate my spend". Produces an A/B
  harness that measures the token drop and confirms answers stay correct.
when_to_use:
  - "Your Anthropic/OpenAI bill is dominated by OUTPUT/completion tokens, not input"
  - "The model writes long preambles ('Certainly! Here is...') and restates the question before answering"
  - "Chain-of-thought reasoning is correct but 5-10x longer than it needs to be"
  - "Tool-use loops emit verbose JSON and re-explain each call"
  - "You want a hard ceiling on generation length without truncating mid-answer"
  - "You need the SAME answer quality at a fraction of the output length, and proof it held"
when_not_to_use:
  - "You want to cut INPUT tokens by ordering context for cache hits -> cache-aware-context-layout"
  - "You want to skip generation entirely by reusing a prior answer -> semantic-response-cache"
  - "You want to run non-urgent jobs at 50% off overnight -> batch-api-offloader"
  - "You want to route easy requests to a cheaper model tier -> model-triage-router"
  - "You just want a running $ estimate of a call before sending it -> llm-cost-estimator"
keywords: [output tokens, completion tokens, chain of draft, chain-of-draft, cod, verbose responses, max_tokens, stop_sequences, structured output, json schema, terse prompting, thinking budget, token-efficient tool use, reduce generation cost, rambling, preamble, concise, response length]
similar_to: [cache-aware-context-layout, semantic-response-cache, batch-api-offloader, model-triage-router, llm-cost-estimator]
inputs_needed:
  - "A representative prompt (or 5-20) whose output you want to shrink, ideally with expected answers to check quality held"
  - "Provider + model (Anthropic Claude 4+ or OpenAI) and API key in env"
  - "Whether the output must stay machine-parseable (JSON/enum) or free text"
produces: An A/B harness that runs each prompt baseline-vs-dieted, reports output-token reduction % and cost saved, and flags any answer that changed.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Output Token Diet

Output tokens cost ~4-5x more than input tokens on every major provider, and
unlike input they can't be prompt-cached. Yet most of a completion is fat:
"Certainly! Here's what I found…" preambles, restating the question, verbose
chain-of-thought, JSON with redundant keys, and a summarizing outro. This skill
strips that fat with six levers, then **proves** the answer survived with an A/B
harness. Realistic combined drop: **40-70%** of output tokens.

This is generation-side savings. It does NOT reorder input for cache hits
(`cache-aware-context-layout`), reuse a prior answer (`semantic-response-cache`),
or move work to the batch tier (`batch-api-offloader`).

## The six levers (biggest wins first)

1. **Chain-of-Draft (CoD) reasoning** — the single biggest lever on reasoning
   tasks. Instead of verbose chain-of-thought, instruct the model to keep each
   reasoning step to ~5 words, then give the answer. Paper (Xu et al., 2025)
   reports CoD uses **as little as ~7.6%** of CoT's tokens at comparable
   accuracy on arithmetic/commonsense tasks.
2. **Terse-response prompting** — ban preamble/postamble. "No preamble. Answer
   only. No restating the question." Kills 10-40 tokens per call, compounding.
3. **Structured / JSON output** — a strict schema forces compactness and stops
   prose padding. Use short keys, enums, and IDs instead of full sentences.
4. **`max_tokens` ceiling + `stop_sequences`** — a hard cap so a runaway can't
   bill you 4096 tokens. `stop_sequences` ends generation the instant the answer
   is done (e.g. stop at `\n\n` or `</answer>`).
5. **Capped thinking/reasoning budget** — set an explicit low `budget_tokens`
   (Claude extended thinking) or `reasoning_effort: "low"` (OpenAI) so internal
   reasoning — which you're billed for — doesn't balloon.
6. **Token-efficient tool use** — built into all **Claude 4+** models by
   default; nothing to enable. (The legacy beta header
   `token-efficient-tools-2025-02-19` now has NO effect and should be removed
   from old code. It applied only to Claude 3.7 Sonnet.)

## Prerequisites

```bash
pip install anthropic tiktoken     # tiktoken only for OpenAI local counting
export ANTHROPIC_API_KEY=sk-ant-...
# or: pip install openai; export OPENAI_API_KEY=sk-...
```

Token counts: use the `usage` block the API returns (`output_tokens` on
Anthropic, `completion_tokens` on OpenAI) — that is what you're billed for. Don't
estimate with a local tokenizer when the real number is in the response.

## Recipe A — Chain-of-Draft + terse system prompt (Anthropic)

The two-line system prompt below is the highest-ROI change for reasoning work.

```python
import anthropic
client = anthropic.Anthropic()

COD_SYSTEM = (
    "Think step by step, but keep each reasoning step to at most 5 words. "
    "Then output only the final answer after '####'. "
    "No preamble, no restating the question, no summary."
)

def ask(prompt: str, system: str, max_tokens: int = 512):
    r = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
        stop_sequences=["\n\n\n"],   # kill any trailing outro
    )
    text = r.content[0].text
    answer = text.split("####")[-1].strip() if "####" in text else text.strip()
    return answer, r.usage.output_tokens

VERBOSE = "Answer the question, showing your reasoning."
q = "A shop had 23 apples, used 20, then bought 6 more. How many now?"
print(ask(q, VERBOSE))     # ~120 out tokens, correct
print(ask(q, COD_SYSTEM))  # ~15 out tokens, correct
```

CoD needs a few worked examples for best results on hard tasks — add 1-3
few-shot pairs that themselves use ≤5-word steps, so the model copies the style.

## Recipe B — Structured output kills prose padding

Free-text "explain the sentiment" bleeds tokens. A schema forces the minimum.

```python
tool = {
    "name": "emit",
    "description": "Return the classification.",
    "input_schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": ["pos", "neg", "neu"]},
            "conf":  {"type": "number"},
        },
        "required": ["label", "conf"],
    },
}

r = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=64,
    tools=[tool],
    tool_choice={"type": "tool", "name": "emit"},   # force the schema, no prose
    messages=[{"role": "user", "content": f"Sentiment: {review!r}"}],
)
# structured result in r.content[0].input; enums + short keys = tiny output
```

OpenAI equivalent: `response_format={"type": "json_schema", ...}` with
`strict: true`, plus `"reasoning_effort": "low"` on o-series / GPT-5 models.

## Recipe C — Caps that stop runaway generation

- `max_tokens`: set to the 95th-percentile length you actually need, not 4096.
  It's a ceiling, not a target — the model still stops early when done.
- `stop_sequences`: end at the natural boundary. If you ask for one JSON object,
  `stop_sequences=["}\n"]` (then re-append `}`) or a sentinel like `</done>`.
- Extended thinking budget (Claude): keep it small when the task is easy.

```python
r = client.messages.create(
    model="claude-sonnet-4-5", max_tokens=1024,
    thinking={"type": "enabled", "budget_tokens": 1024},  # cap billed reasoning
    messages=[{"role": "user", "content": q}],
)
```

## Recipe D — The A/B harness (measure, don't guess)

Copy `scripts/diet_ab.py`. It runs each prompt baseline vs dieted, prints the
per-prompt and mean output-token reduction, dollar saving, and flags any prompt
whose answer changed so you catch quality regressions.

```bash
python scripts/diet_ab.py prompts.jsonl        # {"prompt": "...", "expect": "42"} per line
```

Only ship a lever if the harness shows tokens down AND answers unchanged.

## Verify

- Compare `usage.output_tokens` (Anthropic) / `completion_tokens` (OpenAI)
  before vs after — the harness prints the delta. Expect 40-70% combined.
- Spot-check that no answer got truncated: if the finish/stop reason is
  `max_tokens` (Anthropic `stop_reason == "max_tokens"`), your cap is too low —
  raise it; truncation is a silent quality loss, not a saving.
- Re-run the harness on the full prompt set; the "answer changed" count must be
  0 (or within your accepted tolerance) before rollout.

## Pitfalls

- **`max_tokens` too tight truncates the answer.** A cut-off answer isn't
  cheaper, it's wrong. Size the cap to real p95 length and watch `stop_reason`.
- **Over-terse prompts lower accuracy on hard reasoning.** CoD trades some
  headroom for tokens; on the hardest tasks keep normal thinking or add few-shot
  CoD exemplars. Always gate on the harness.
- **Don't chase the legacy header.** `token-efficient-tools-2025-02-19` does
  nothing on Claude 4+ — remove it; efficiency is built in.
- **Structured output can raise input tokens** (the schema/tool def). It's still
  a net win when output shrinks more, but confirm with the harness, not vibes.
- **Streaming doesn't reduce token count** — you're billed for every token
  streamed. It only lets you *cancel* early; wire an abort if you detect the
  answer is complete mid-stream.
- **Reasoning/thinking tokens are billed output tokens.** Capping `max_tokens`
  alone won't shrink them — set `budget_tokens` / `reasoning_effort` too.
