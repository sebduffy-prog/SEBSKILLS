---
name: context-quality-evals
category: context-engineering
description: >
  Evaluate the CONTEXT itself, not just the model — run needle-in-a-haystack / RULER-style
  sweeps, lost-in-the-middle position tests, distractor-robustness, and needle-question
  similarity, then chart exactly where a model degrades vs input length and needle depth.
  Use when you ask "does my model actually use its full context window", "is my long prompt
  suffering context rot", "run a needle in a haystack test", "RULER benchmark", "lost in the
  middle", "why does accuracy drop past 32k tokens", "test distractor robustness", or "how long
  a context can I trust". Produces a length×depth accuracy heatmap and a per-cell CSV.
when_to_use:
  - "You stuffed a long document / big prompt into the window and want to know if the model actually retrieves from all of it"
  - "Deciding the real usable context length before a model degrades (not the marketing number)"
  - "Reproducing NVIDIA RULER or Chroma context-rot to compare models on long-context retrieval"
  - "Suspect lost-in-the-middle — needles early vs middle vs late retrieve differently"
  - "Testing distractor robustness: does a competing/near-duplicate passage cause wrong answers or hallucinations"
  - "Charting accuracy vs input length to justify a chunking / compaction / budget decision"
when_not_to_use:
  - "You already know the model rots and just need to shrink the prompt — use prompt-compression or agent-context-compaction"
  - "Deciding what to keep vs drop under a token budget — use context-window-budgeter"
  - "Measuring RAG retrieval quality (recall@k, nDCG, faithfulness) rather than the model's in-context reading — use rag/llm-rag-eval-harness"
  - "Organising long-lived memory across a session — use structured-memory-layers or agent-memory-file"
  - "Isolating context per subagent to avoid pollution — use subagent-context-isolation"
keywords: [needle in a haystack, niah, ruler, context rot, lost in the middle, long context eval, distractor robustness, context quality, effective context length, position bias, retrieval degradation, longmemeval, context window test, haystack, needle depth, semantic needle, context-rot chroma]
similar_to: [context-window-budgeter, prompt-compression, agent-context-compaction, subagent-context-isolation, structured-memory-layers]
inputs_needed:
  - "Which model(s) and provider (Anthropic / OpenAI / vLLM / HF) — and an API key or local weights"
  - "Which context lengths to sweep (e.g. 4k, 16k, 64k, 128k) and how many needle depths"
  - "Whether to test distractors and/or semantic (non-lexical) needles, or just plain retrieval"
  - "A budget: sweeps are N_lengths × N_depths × N_trials API calls — cap it before spending"
produces: A length×depth accuracy heatmap (PNG) plus a per-cell CSV showing exactly where the model's in-context retrieval degrades
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Context Quality Evals — is your context actually being used?

A bigger context window is not a bigger *usable* window. Models retrieve reliably from short
inputs and degrade — often non-monotonically — as the input grows, even on trivial tasks. This
skill measures **the quality of the context you hand the model**: where in a long input the model
stops finding the needle, how distractors and coherence flip answers into hallucinations, and what
your *effective* (not advertised) context length really is.

Two grounding references, both with public code:

- **NVIDIA/RULER** (`github.com/NVIDIA/RULER`) — the standard synthetic long-context benchmark.
  4 categories: **retrieval** (single/multi-key/value/query NIAH), **multi-hop tracing**
  (variable_tracking), **aggregation** (common_words / freq_words extraction), **QA** (SQuAD,
  HotpotQA). Sweeps 4K→128K. A model "passes" a length only if it beats Llama-2-7B's 4K score
  (~85.6%); most 32K+ claims fail well before their advertised length.
- **Chroma context-rot** (`github.com/chroma-core/context-rot`) — 18 models across: extended NIAH
  with **semantic** (non-lexical) needles, **needle-question similarity**, **distractors**
  (0/1/4 competing answers), **LongMemEval** (~113k-token chat histories), and **repeated words**.
  Headline findings you can reproduce: accuracy degrades with length even on trivial tasks; a
  single distractor drops accuracy and more compound it; **lost-in-the-middle** is real (early
  needles win); and, counter-intuitively, a **shuffled/incoherent haystack outperforms a coherent
  one**.

## When to use

Reach for this when the failure mode is *"the answer was in the prompt but the model missed it"* —
before you blame the model, or before you commit to a context length, a chunk size, or a compaction
threshold. Run it to get a defensible number: "this model is reliable to ~48k tokens on our task,
then falls off a cliff at depth 0.5."

## Prerequisites

- An API key or local weights for the model(s) under test:
  `export ANTHROPIC_API_KEY=…` and/or `export OPENAI_API_KEY=…`.
- **For the bundled quick harness (`scripts/niah_sweep.py`)**: Python 3.9+, stdlib only to run the
  calls; `pip install matplotlib` only if you want the heatmap PNG. No GPU.
- **For full RULER**: it is heavy — Docker (`cphsieh/ruler:0.2.0`) or a GPU box with vLLM/TensorRT-LLM/HF.
  API-only models (OpenAI/Gemini) run through its `openai`/`gemini` framework without a GPU.
- **For Chroma context-rot**: `python -m venv venv && pip install -r requirements.txt`; set
  `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_APPLICATION_CREDENTIALS` as needed.

## Recipe 1 — Fast local sweep (no GPU, minutes) with the bundled harness

The quickest way to see *your* model's cliff. It builds a boring filler haystack, inserts one
needle at a fractional depth, optionally adds competing distractors, and grades exact-match.

```bash
cd scripts
export ANTHROPIC_API_KEY=sk-...
python3 niah_sweep.py \
  --provider anthropic --model claude-sonnet-4-5 \
  --lengths 2000 8000 32000 128000 \
  --depths 0 0.25 0.5 0.75 1.0 \
  --distractors 0 \
  --trials 3 \
  --out sonnet_sweep.csv --heatmap sonnet_sweep.png
```

Read the printed grid (rows = depth, cols = length) for the degradation surface. Green cells =
reliable, red = the model is missing needles there. Then re-run with `--distractors 1 4` to
measure robustness — a big drop from `dist=0` to `dist=1` is the "single competing passage flips
the answer" effect from context-rot.

**Lost-in-the-middle read**: within a fixed length column, if `depth 0.0` (top) and `depth 1.0`
(bottom) are green but `depth 0.5` is red, that is the classic middle sag — put critical context at
the edges of the window, not buried.

> The harness is deliberately small and lexical-exact. For semantic needles, multi-needle, and the
> shuffled-vs-coherent haystack ablation, use Recipe 2/3 which reproduce the published batteries.

## Recipe 2 — Reproduce Chroma context-rot (semantic needles, distractors, LongMemEval)

```bash
git clone https://github.com/chroma-core/context-rot && cd context-rot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=... ANTHROPIC_API_KEY=...

# Each experiment is self-contained under experiments/ with its own README:
cd experiments/niah_extension    # semantic (non-lexical) needle + haystack variations
cat README.md                     # follow the per-experiment run + plotting commands
cd ../repeated_words              # exact-reproduction task, 25→10,000 words
cd ../longmemeval                 # conversational QA over ~113k-token histories
```

Use this when you specifically want the **semantic-match**, **needle-question-similarity**, and
**distractor-count (0/1/4)** curves, or the **coherent-vs-shuffled haystack** ablation — none of
which the plain lexical harness gives you.

## Recipe 3 — Reproduce NVIDIA RULER (the standard benchmark)

```bash
docker pull cphsieh/ruler:0.2.0            # or build from docker/Dockerfile
# prepare source data (Paul Graham essays + SQuAD/HotpotQA):
cd scripts/data/synthetic/json
python download_paulgraham_essay.py && bash download_qa_dataset.sh
cd ../../..
# edit run.sh (GPUS, ROOT_DIR, MODEL_DIR/ENGINE_DIR) and config_models.sh
#   MODEL_FRAMEWORK: hf | vllm | trtllm | openai | gemini
#   MODEL_TEMPLATE_TYPE: base | meta-chat | ... (add new templates in scripts/data/template.py)
bash run.sh YOUR_MODEL_NAME synthetic
```

Task complexity is set in `scripts/config_tasks.sh` and `scripts/synthetic.yaml`; sequence lengths
default to 4K/8K/16K/32K/64K/128K. For an **API model with no GPU**, set
`MODEL_FRAMEWORK=openai` (or `gemini`) and point `MODEL_PATH` at the API model name.

## Verify

- **Sanity floor**: at your shortest length + `depth 0` + `dist 0`, accuracy should be ~1.0. If not,
  your grader or prompt is broken, not the model — fix that before trusting any cell.
- **Token sizing**: the harness sizes by ~0.75 words/token; confirm the true token count of a built
  prompt with your provider's tokenizer if a length boundary matters (e.g. the 128k edge).
- **Cross-check**: the *shape* of your curve (degrades with length, sags in the middle, drops under
  distractors) should match the published RULER/context-rot trends. A perfectly flat 1.0 across
  128k usually means the needle is too lexically obvious — make it semantic (Recipe 2).
- **Effective length**: report the largest length whose *worst-depth* cell still clears your task
  threshold (RULER uses ~85.6%). That single number is the deliverable.

## Pitfalls

- **Lexical leakage inflates scores.** If the needle shares rare words with the question, the model
  matches on surface form and you overestimate real retrieval. Use semantic needles (Recipe 2) for
  an honest number.
- **One trial per cell is noise.** Long-context accuracy is high-variance across seeds/positions;
  run `--trials 3+` and average, or you will chase phantom cliffs.
- **Averaging over depth hides lost-in-the-middle.** Always keep the depth axis separate — a 0.8
  mean can be 1.0 at the edges and 0.4 in the middle. The middle is what bites you in production.
- **Coherent haystacks can score *worse* than shuffled ones** (a real context-rot finding). Don't
  assume "more natural context = better"; test it, and don't design a haystack that accidentally
  helps or hurts.
- **This measures the model reading context, not your retriever.** If the needle never makes it into
  the prompt, that is a RAG problem — go to `rag/llm-rag-eval-harness`, not here.
- **RULER is not laptop-friendly.** Full local weights need a GPU; if you only have an API key, use
  RULER's `openai`/`gemini` framework or stick to the bundled harness / Recipe 2.
- **Budget explodes multiplicatively.** lengths × depths × distractors × trials calls, some at 128k
  tokens each — price it before you launch. Start coarse (3 lengths, 3 depths, 1 trial), then refine
  around the cliff.

## Acting on the result

The chart is a means, not the end — feed the number into a fix:
- Cliff too low for your prompt size → **prompt-compression** or **agent-context-compaction** to fit
  under it.
- Deciding what survives the budget → **context-window-budgeter**.
- Middle sag → reorder so load-bearing context sits at the window edges, or split across
  **subagent-context-isolation** so no single window carries it all.
