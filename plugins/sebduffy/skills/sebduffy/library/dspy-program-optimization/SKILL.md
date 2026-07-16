---
name: dspy-program-optimization
category: agent-frameworks
description: >
  Build and optimize LLM programs with DSPy instead of hand-tuning prompt strings. Define typed Signatures,
  compose Modules (Predict, ChainOfThought, ReAct), then let self-improving optimizers (GEPA, MIPROv2,
  BootstrapFewShot) compile prompts and few-shot demos against a metric on your trainset. Use when the user
  says "optimize my prompt", "DSPy", "compile a prompt", "self-improving pipeline", "GEPA", "MIPROv2",
  "few-shot bootstrapping", "stop hand-tuning prompts", or wants a measurable, retrainable LLM program.
when_to_use:
  - "You have a task + a metric + example data and want prompts/few-shots tuned automatically, not by hand"
  - "User says 'use DSPy' or names an optimizer: GEPA, MIPROv2, BootstrapFewShot, BootstrapFinetune"
  - "A multi-step LLM pipeline (RAG, classify, extract, ReAct agent) whose accuracy you must measurably raise"
  - "You want a program that survives model swaps (GPT to Claude) by recompiling rather than rewriting prompts"
  - "You need reflective prompt evolution from textual feedback (GEPA) on a small budget of rollouts"
when_not_to_use:
  - "Pure prompt A/B iteration without a code framework — use prompt-optimization"
  - "Durable, checkpointed multi-agent workflows — use langgraph-durable-workflows"
  - "Typed agents with tool-calls as the primary need, no optimizer — use pydantic-ai-typed-agents or openai-agents-sdk"
  - "Just want structured JSON out of one call — use instructor-structured-outputs or baml-structured-prompts"
keywords: [dspy, gepa, miprov2, bootstrapfewshot, prompt optimization, teleprompter, signature, chainofthought, react, compile prompt, self-improving, few-shot bootstrapping, dspy.LM, reflective optimizer, stanfordnlp, metric-driven, prompt compiler]
similar_to: [prompt-optimization, pydantic-ai-typed-agents, baml-structured-prompts, instructor-structured-outputs, agent-evals-and-tracing]
inputs_needed:
  - "The task framed as inputs -> outputs (so a Signature can be written)"
  - "A metric function (exact match, F1, LLM-judge, or a custom scorer) that returns higher=better"
  - "A trainset (and ideally a valset) of dspy.Example rows — even 20–50 helps"
  - "An LM + API key (OpenAI/Anthropic/local via LiteLLM); GEPA also needs a stronger reflection_lm"
produces: A compiled DSPy program (saved .json of optimized instructions + demos) plus an eval score before/after
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# DSPy Program Optimization

Program LLMs, don't prompt them. You write **Signatures** (typed I/O contracts) and compose **Modules**;
an **optimizer** searches instructions and few-shot demos to maximize your **metric** on your data. Output
is a saved artifact you reload — and recompile when you swap models.

## When to use

Reach for DSPy when you have (1) a task expressible as inputs->outputs, (2) a metric, and (3) some examples.
If any of those is missing, gather it first — an optimizer with no metric is just a prompt string.

## Prerequisites

```bash
pip install -U dspy        # v3.x (verified 3.3.x). Package name is `dspy` (old `dspy-ai` is deprecated).
```

DSPy calls models through LiteLLM, so provider strings look like `openai/…`, `anthropic/…`, `ollama_chat/…`.
Set the matching key:

```bash
export OPENAI_API_KEY=sk-...        # or ANTHROPIC_API_KEY=... for anthropic/ models
```

Configure once at startup:

```python
import dspy
dspy.configure(lm=dspy.LM("openai/gpt-4o-mini", max_tokens=1000))
# Anthropic: dspy.LM("anthropic/claude-sonnet-4-5")
# Local:     dspy.LM("ollama_chat/llama3.2", api_base="http://localhost:11434")
```

## Recipe 1 — Signature + Module (the program)

Inline string signatures for quick tasks; class-based for docstring guidance and typed fields.

```python
import dspy

# Inline: "inputs -> outputs"
classify = dspy.Predict("text -> sentiment: str")
print(classify(text="the food was cold and late").sentiment)

# Class-based signature — docstring is the task instruction the optimizer will rewrite.
class RateSupportReply(dspy.Signature):
    """Judge whether a support reply resolves the customer's issue."""
    ticket: str = dspy.InputField()
    reply: str = dspy.InputField()
    resolved: bool = dspy.OutputField()
    reason: str = dspy.OutputField(desc="one sentence")

judge = dspy.ChainOfThought(RateSupportReply)   # adds a reasoning field automatically
out = judge(ticket="wifi down 3 days", reply="Have you tried rebooting?")
print(out.resolved, out.reason)      # access via attributes on the Prediction
```

Modules you compose: `dspy.Predict` (raw), `dspy.ChainOfThought` (adds rationale), `dspy.ReAct(sig, tools=[...])`
(tool-using agent loop). Build multi-step programs by subclassing `dspy.Module`:

```python
class RAG(dspy.Module):
    def __init__(self):
        self.retrieve = dspy.Retrieve(k=3)
        self.answer = dspy.ChainOfThought("context, question -> answer")
    def forward(self, question):
        ctx = self.retrieve(question).passages
        return self.answer(context=ctx, question=question)
```

## Recipe 2 — Data + metric

```python
# Examples: mark which fields are inputs with .with_inputs()
trainset = [
    dspy.Example(text="loved it, five stars", sentiment="positive").with_inputs("text"),
    dspy.Example(text="never again", sentiment="negative").with_inputs("text"),
    # ... aim for 20–50+ rows; split off a valset
]

# Metric: (example, prediction, trace=None) -> higher is better. trace is passed during bootstrapping.
def metric(example, pred, trace=None):
    return example.sentiment.lower() == pred.sentiment.lower()

# Built-ins exist too: dspy.evaluate.answer_exact_match, answer_passage_match, SemanticF1.
```

Measure the baseline before optimizing so you can prove the lift:

```python
from dspy.evaluate import Evaluate
evaluator = Evaluate(devset=valset, metric=metric, num_threads=8, display_progress=True)
evaluator(classify)      # prints baseline score
```

## Recipe 3 — Optimize (compile). Pick by budget/data

Every optimizer is `Optimizer(metric=...).compile(student=program, trainset=..., valset=...)` and returns a
**new** compiled program (immutable — the original is untouched).

```python
# A) Cheapest, needs least data — bootstrap few-shot demos from the trainset:
opt = dspy.BootstrapFewShot(metric=metric, max_bootstrapped_demos=4, max_labeled_demos=4)
compiled = opt.compile(student=classify, trainset=trainset)

# B) Instruction + demo search (great default when you have a valset):
opt = dspy.MIPROv2(metric=metric, auto="light", num_threads=8)   # auto: "light"|"medium"|"heavy"
compiled = opt.compile(student=classify, trainset=trainset, valset=valset)

# C) GEPA — reflective prompt evolution from *textual feedback*; strong at low rollout budgets.
#    Requires a capable reflection_lm and a feedback-returning metric (5-arg form):
def gepa_metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
    ok = gold.sentiment.lower() == pred.sentiment.lower()
    fb = "correct" if ok else f"expected {gold.sentiment}, got {pred.sentiment}"
    return dspy.Prediction(score=float(ok), feedback=fb)   # score + natural-language feedback

opt = dspy.GEPA(metric=gepa_metric, auto="light",
                reflection_lm=dspy.LM("openai/gpt-4o", temperature=1.0, max_tokens=8000))
compiled = opt.compile(student=classify, trainset=trainset, valset=valset)
```

Choosing: **BootstrapFewShot** for <~50 rows / smoke tests; **MIPROv2** for joint instruction+demo tuning when
you can afford dozens of trials; **GEPA** when each rollout is expensive and you want language-level reasoning
about failures. `BootstrapFinetune` distills the compiled prompt into fine-tuned weights.

## Recipe 4 — Evaluate the lift, save, reload

```python
evaluator(compiled)                 # compare to the baseline you took in Recipe 2
compiled.save("classifier_v1.json") # plain-text JSON: optimized instructions + demos

# Later / in prod:
loaded = dspy.Predict("text -> sentiment: str")
loaded.load("classifier_v1.json")
```

## Verify

- `python -c "import dspy; print(dspy.__version__)"` → 3.x.
- Baseline score printed, compiled score printed, compiled > baseline (or investigate the metric/data).
- `dspy.inspect_history(n=1)` shows the exact prompt actually sent — confirm the optimized instruction/demos are in it.
- The saved `.json` exists and reloads without error; a fresh process reproduces the compiled score.

## Pitfalls

- **No metric = no optimization.** Booleans/floats where higher is better. A noisy metric optimizes noise.
- **Package name:** `pip install dspy` (not `dspy-ai`, which is the deprecated alias). Import is `import dspy`.
- **Provider prefix required:** `dspy.LM("gpt-4o")` fails; use `"openai/gpt-4o"`. Missing key → LiteLLM auth error.
- **`.with_inputs()` is mandatory** on Examples — untagged fields are treated as labels, and the module gets no input.
- **GEPA specifics:** metric must return `dspy.Prediction(score=, feedback=)` (or a float), and `reflection_lm` should
  be a *stronger/larger* model than the task LM — that's where the improvement reasoning happens.
- **Cost/latency:** `auto="heavy"` and large `num_threads` fan out many calls. Start `auto="light"`, small trainset,
  cheap task LM; scale up only after the loop works end to end.
- **Optimizers are pure:** `compile()` returns a new program; keep the return value — the `student` you passed in is unchanged.
- **Recompile on model swap.** A prompt optimized for one model is not optimal for another — rerun `compile()` after switching LMs.
