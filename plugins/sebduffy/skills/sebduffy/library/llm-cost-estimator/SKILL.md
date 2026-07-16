---
name: llm-cost-estimator
category: model-routing
description: >
  Price an LLM call in USD BEFORE you run it. Count prompt tokens, multiply by per-model rates for
  400+ models (tokencost / LiteLLM pricing tables), add an assumed output length, and hard-cap the
  spend so runaway calls never fire. Use when someone says "how much will this cost", "estimate token
  cost", "count tokens before sending", "budget guard", "cap the spend per call", "price this prompt",
  "cost per 1k tokens", "which model is cheaper for this request", or "don't let this call exceed $X".
  Produces a Decimal-precise USD estimate + a pass/fail budget gate.
when_to_use:
  - "How much will this prompt cost on gpt-4o vs claude before I actually send it?"
  - "Count the tokens in this request and give me a dollar figure"
  - "Add a hard budget cap so a call over $0.05 refuses to run"
  - "Compare per-request cost across several candidate models to pick the cheapest that fits"
  - "Log estimated vs actual spend per call / per user for a dashboard"
  - "Warn me when a context window is about to blow past a model's max tokens"
when_not_to_use:
  - "Decide WHICH model handles a request by difficulty — use model-triage-router"
  - "Try a cheap model first then escalate on low confidence — use model-cascade-escalation"
  - "Put one OpenAI-compatible endpoint in front of many vendors — use cross-provider-gateway"
  - "Shrink the actual output length to save money at generation time — use output-token-diet"
  - "Track real post-hoc spend from provider usage headers only — LiteLLM's response_cost covers that"
keywords: [tokencost, litellm, token counting, cost estimation, usd, budget cap, price prompt, cost per token, tiktoken, completion_cost, cost_per_token, count_message_tokens, calculate_prompt_cost, model pricing, spend guard, pre-flight, tokens, max tokens, decimal]
similar_to: [model-triage-router, cross-provider-gateway, model-cascade-escalation, output-token-diet, batch-api-offloader]
inputs_needed:
  - The prompt/messages (string or ChatML array) to be priced
  - Target model name(s) — e.g. gpt-4o, claude-sonnet-4-5, gemini/gemini-1.5-pro
  - Expected output length in tokens (estimate; output isn't generated yet)
  - Optional hard cap in USD and whether a breach should fail or just warn
produces: A Decimal-precise USD cost estimate (prompt + expected output) plus a pass/fail budget-cap verdict
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# LLM Cost Estimator — price the call before you run it

Turn "will this prompt bankrupt me?" into a number you can gate on. This skill counts prompt tokens,
looks up per-model input/output rates for **400+ models**, adds an assumed output length, and returns
a **Decimal-precise USD** figure — all with **zero API calls**. Bolt a budget cap on top so any call
whose estimate exceeds a threshold refuses to fire.

Two grounded backends, same idea:

| Backend | Best when | Pricing source |
|---------|-----------|----------------|
| **tokencost** (AgentOps-AI) | you want a tiny, focused lib returning `Decimal` USD | LiteLLM `model_prices` JSON |
| **litellm** | you already depend on LiteLLM / want its live `response_cost` too | same JSON, in-lib |

> This is **pricing + gating only**. Choosing which model to route to is `model-triage-router`;
> escalating cheap→expensive is `model-cascade-escalation`; trimming the real output is `output-token-diet`.

## Prerequisites

- Python 3.9+.
- **tokencost path:** `pip install tokencost` (pulls `tiktoken`, `anthropic`). Returns `Decimal` USD.
- **litellm path:** `pip install litellm`.
- **No LLM API key needed** for estimation — pricing tables ship with the packages and token
  counting is local (`tiktoken` for OpenAI-family; tokencost calls Anthropic's local counter for Claude models).
- Pricing tables are baked into the installed version — `pip install -U` periodically so rates stay current.

---

## Recipe A — tokencost: price a prompt (no API call)

`tokencost` returns **`Decimal`** in USD (not float) — keep it as Decimal for money math; cast to
`float` only at display time.

```python
from decimal import Decimal
from tokencost import (
    count_message_tokens, count_string_tokens,
    calculate_prompt_cost, calculate_completion_cost,
    calculate_all_costs_and_tokens,
)

messages = [{"role": "user", "content": "Summarise the attached contract in 5 bullets."}]
model = "gpt-4o"

n_prompt = count_message_tokens(messages, model)          # -> int
prompt_usd = calculate_prompt_cost(messages, model)       # -> Decimal, USD

# You haven't generated the output yet, so price a *sample* completion of the expected length:
sample = "x " * 400                                        # ~ your expected output
out_usd = calculate_completion_cost(sample, model)         # -> Decimal, USD
print(n_prompt, prompt_usd, out_usd, prompt_usd + out_usd)
```

After a real call, price prompt+completion together for logging:

```python
row = calculate_all_costs_and_tokens(messages, actual_completion_text, model)
# {'prompt_cost': Decimal(...), 'prompt_tokens': int,
#  'completion_cost': Decimal(...), 'completion_tokens': int}
```

Price by a **known token count** (when you have a length target, not text) — the cleanest way to
model expected output:

```python
from tokencost import calculate_cost_by_tokens
out_usd = calculate_cost_by_tokens(num_tokens=800, model=model, token_type="output")  # Decimal
in_usd  = calculate_cost_by_tokens(num_tokens=n_prompt, model=model, token_type="input")
```

## Recipe B — litellm: same estimate, plus live actual cost

```python
from litellm import token_counter, cost_per_token, completion_cost, get_max_tokens

messages = [{"role": "user", "content": "Say this is a test"}]
model = "claude-sonnet-4-5"

n = token_counter(model=model, messages=messages)                     # int, local
p_cost, c_cost = cost_per_token(model=model, prompt_tokens=n, completion_tokens=800)  # (float, float) USD
print(get_max_tokens(model))                                          # context ceiling

# Post-hoc: LiteLLM attaches response_cost to every completion() response, or:
usd = completion_cost(model=model, prompt="Hey!", completion="How's it going?")
```

## Recipe C — hard budget cap (the guard)

Use the bundled helper to fail-fast when an estimate breaches a cap. Wire it into any call site so
a too-expensive request never reaches the provider.

```bash
# text prompt on stdin, cap at 5 cents, assume ~800 output tokens:
echo "Draft a 2000-word market report on Q3 ad spend." \
  | python scripts/budget_guard.py --model gpt-4o --expected-output-tokens 800 --max-usd 0.05
# JSON estimate to stdout; exit code 2 (or a warning with --warn-only) if over cap
```

```python
from scripts.budget_guard import estimate, guard, BudgetExceeded
try:
    est = guard(estimate(messages, "gpt-4o", expected_output_tokens=800), max_usd=0.05)
    # ...safe to call the model...
except BudgetExceeded as e:
    downgrade_or_reject(e)   # route to a cheaper model, truncate, or refuse
```

## Recipe D — compare models, pick cheapest that fits

```python
from tokencost import calculate_prompt_cost, calculate_cost_by_tokens
candidates = ["gpt-4o-mini", "gpt-4o", "claude-sonnet-4-5", "gemini/gemini-1.5-pro"]
expected_out = 800
priced = []
for m in candidates:
    try:
        total = calculate_prompt_cost(messages, m) + calculate_cost_by_tokens(expected_out, m, "output")
        priced.append((m, total))
    except Exception:      # model not in pricing table for this backend version
        continue
for m, total in sorted(priced, key=lambda x: x[1]):
    print(f"{m:28} ${float(total):.6f}")
```

## Verify

```bash
python -c "from tokencost import calculate_prompt_cost; print(calculate_prompt_cost([{'role':'user','content':'hi'}],'gpt-4o'))"
# prints a Decimal like 0.00000... > 0

python scripts/budget_guard.py --help                 # arg parsing OK
echo "hello" | python scripts/budget_guard.py --model gpt-4o --max-usd 999   # exit 0, JSON estimate
echo "$(python3 -c 'print("word "*5000)')" | python scripts/budget_guard.py --model gpt-4o --max-usd 0.0001 --expected-output-tokens 2000; echo "exit=$?"  # exit 2
```

## Pitfalls

- **Decimal, not float.** tokencost returns `Decimal`; adding it to a `float` raises `TypeError`.
  Wrap floats with `Decimal(str(x))` and only cast to float for display.
- **Output isn't free and isn't known.** Prompt cost is exact; output cost is a *forecast* — you must
  supply an expected length. Under-guessing output is the #1 way estimates undershoot the real bill.
- **Unknown / new model names throw.** If a model isn't in the installed pricing table you get a
  KeyError/exception — catch it and `pip install -U tokencost litellm` to refresh rates.
- **Model name aliases differ per backend.** tokencost/LiteLLM expect names like `gpt-4o`,
  `claude-sonnet-4-5`, `gemini/gemini-1.5-pro`. Copy the exact key from `tokencost.TOKEN_COSTS`
  (or `litellm.model_cost`) rather than guessing.
- **Cached / prompt-cache reads are cheaper** than the sticker input rate; a flat estimate over-counts
  cache-hit tokens. For heavy caching, price cached vs fresh tokens separately (see cache-aware-context-layout).
- **Token counts are approximate for non-OpenAI models.** tiktoken is exact for OpenAI; other
  providers use provider counters or heuristics — treat the estimate as a tight bound, not a receipt.
- **Refresh rates.** Pricing is a snapshot in the installed package version. Pin + periodically
  `-U`, or your estimates silently drift from actual invoices.

## Reference

- tokencost (MIT) — https://github.com/AgentOps-AI/tokencost
- LiteLLM token/cost docs — https://docs.litellm.ai/docs/completion/token_usage
