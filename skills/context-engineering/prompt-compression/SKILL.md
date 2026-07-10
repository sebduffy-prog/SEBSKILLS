---
name: prompt-compression
category: context-engineering
description: >
  Shrink bloated prompts, few-shot exemplars and RAG context 2-20x with LLMLingua-2
  token pruning BEFORE they hit the LLM, cutting input-token cost and latency while
  preserving the answer. A small BERT/RoBERTa classifier scores every token and drops
  the low-information ones; you keep punctuation, digits and forced keywords. Use when
  input tokens are the cost driver, retrieved chunks overflow the window, or you want
  a target-token / keep-rate budget on any text you send. Phrasings: "compress the
  prompt", "shrink the context", "reduce input tokens", "prune the RAG chunks",
  "LLMLingua", "make this prompt cheaper", "trim before the API call".
when_to_use:
  - Input/prompt tokens dominate your API bill and you want a 2-20x cut with minimal quality loss
  - Retrieved RAG chunks or pasted documents overflow the context window before generation
  - Long few-shot exemplars or chain-of-thought demos inflate every request
  - You need a hard token budget on a prompt (target_token) or a keep-rate (e.g. keep 33%)
  - You want a preprocessing step that runs locally/cheaply before hitting Claude/GPT
  - Latency matters and a shorter prompt measurably speeds first-token time
when_not_to_use:
  - You want to compact a long multi-turn agent conversation mid-run — use agent-context-compaction
  - You need to measure/allocate token spend per component first — use context-window-budgeter
  - You want to score whether context actually helps retrieval quality — use context-quality-evals
  - You are designing working/episodic/semantic memory tiers — use structured-memory-layers
  - The text is short or already dense (compression overhead > savings)
keywords: [prompt compression, llmlingua, llmlingua-2, token pruning, context compression, rag compression, input token cost, target token, compression rate, few-shot compression, xlm-roberta, promptcompressor, shrink prompt, reduce tokens, microsoft llmlingua, chain-of-thought compression]
similar_to: [agent-context-compaction, context-window-budgeter, context-quality-evals, structured-memory-layers, subagent-context-isolation]
inputs_needed:
  - The text to compress (prompt, RAG chunks, exemplars) and the downstream question if any
  - A budget — either a keep-rate (0.0-1.0) or an absolute target_token count
  - Where it runs (CPU is fine; GPU/mps is faster) and whether pip install is allowed
produces: A compressed prompt string plus origin/compressed token counts, ratio and $ saving
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Prompt Compression (LLMLingua-2)

Long prompts cost money and add latency, but most tokens carry little information.
**LLMLingua-2** (Microsoft) runs a small token-classification model (XLM-RoBERTa /
BERT, ~single forward pass) over your text, scores each token's importance, and
**drops the low-value ones** — no generation, no rewrite, order preserved. Typical
2-5x on prose, up to ~20x on redundant RAG dumps, with the downstream answer largely
intact. It is a **preprocessing step**: compress, then send the smaller prompt to
Claude/GPT.

## When to use

Reach for this when *input* tokens are your cost/latency driver: fat RAG chunks,
long few-shot exemplars, pasted docs, verbose chain-of-thought demos. Not for
compacting a live agent conversation (that is agent-context-compaction) and not for
already-short prompts (the model load + pass costs more than you save).

## Prerequisites

- `pip install llmlingua` — pulls in `torch` + `transformers`. First run downloads
  the compressor model (~a few hundred MB) from HuggingFace, then it's cached.
- CPU works. GPU (`cuda`) or Apple `mps` is faster for big batches. Set via
  `device_map="cpu" | "cuda" | "mps"`.
- **No API key needed** — the compressor runs locally. You still pay tokens on the
  downstream LLM call, just fewer.
- Models (HuggingFace):
  - `microsoft/llmlingua-2-xlm-roberta-large-meetingbank` — best quality, multilingual.
  - `microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank` — smaller/faster.

## Recipe 1 — Compress with a keep-rate

`rate` = fraction of tokens to **keep**. `rate=0.33` keeps ~a third.

```python
from llmlingua import PromptCompressor

compressor = PromptCompressor(
    model_name="microsoft/llmlingua-2-xlm-roberta-large-meetingbank",
    use_llmlingua2=True,          # REQUIRED — selects the LLMLingua-2 path
    device_map="cpu",
)

out = compressor.compress_prompt(
    context,                       # str, or a list[str] of RAG chunks
    rate=0.33,
    force_tokens=["\n", ".", "?", "!", ","],  # never prune these (keep structure)
    drop_consecutive=True,         # collapse repeated force_tokens
)

print(out["compressed_prompt"])
print(out["origin_tokens"], "->", out["compressed_tokens"], out["ratio"], out["saving"])
```

Return dict keys: `compressed_prompt`, `origin_tokens`, `compressed_tokens`,
`ratio` (e.g. `"3.2x"`), `rate`, `saving` (estimated $ saved on GPT-3.5/4 pricing).

## Recipe 2 — Hard token budget (target_token)

When you must fit a window, set an absolute cap instead of a rate:

```python
out = compressor.compress_prompt(
    retrieved_chunks,              # list[str] from your retriever
    target_token=500,             # overrides rate
    question="What is the refund window?",  # bias retention toward the question
    force_tokens=["\n", ".", "?"],
)
```

`question=` conditions token scoring on what you'll ask, so answer-bearing tokens
survive preferentially. Always pass it in a RAG pipeline.

## Recipe 3 — Wire into a RAG call (compress, then generate)

```python
def answer(query, chunks, client):
    packed = compressor.compress_prompt(
        chunks, target_token=800, question=query,
        force_tokens=["\n", ".", "?", "!"],
    )["compressed_prompt"]

    return client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user",
                   "content": f"Context:\n{packed}\n\nQuestion: {query}"}],
    )
```

## Recipe 4 — CLI helper

`scripts/compress.py` wraps the above for files / stdin:

```bash
python scripts/compress.py --in context.txt --rate 0.33
python scripts/compress.py --in chunks.txt --target-token 500 \
       --question "refund policy?" --json
cat notes.md | python scripts/compress.py --rate 0.5 --device mps
```

Prints the compressed text to stdout and the token stats to stderr (`--json` emits
everything as one object).

## Verify

- **It actually shrank:** `compressed_tokens < origin_tokens` and `ratio` > 1x.
- **Answer preserved:** run your eval set through compressed vs. uncompressed context
  and compare accuracy/EM/F1. Tune `rate`/`target_token` to the highest compression
  that holds quality (start ~0.5, push toward 0.33 while accuracy holds).
- **Net win:** time the compress step; if compression latency + saved-token time <
  original, keep it. For tiny prompts it won't be — skip them.

## Pitfalls

- **`use_llmlingua2=True` is mandatory** — omit it and you get the slower LLMLingua-1
  (perplexity/LLM-based) path, not the fast token classifier.
- **First call is slow** — model download + load. Instantiate `PromptCompressor`
  **once** and reuse it; never build it per request.
- **`rate` keeps, not drops.** `rate=0.33` keeps 33%. Easy to invert mentally.
- **Compressed text reads as fragments** — that's expected; LLMs handle it fine, but
  don't show it to end users as-is.
- **Protect the essentials:** put digits, delimiters, JSON/markdown punctuation in
  `force_tokens` (and `force_reserve_digit=True` for numeric-heavy data) or the model
  may prune tokens your downstream parsing needs.
- **Not free on short inputs** — the model pass has fixed overhead; only compress when
  input tokens are genuinely the bottleneck.
- **Measure quality per domain** — MeetingBank-trained models generalize well but
  verify on YOUR data before trusting aggressive rates in production.
