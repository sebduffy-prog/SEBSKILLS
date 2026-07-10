---
name: agent-evals-and-tracing
category: agent-frameworks
description: >
  Evaluate and trace agentic LLM systems end to end — score whole trajectories and tool-call
  accuracy, choose deterministic (final-state / exact-match) vs LLM-as-judge grading, measure
  reliability with pass^k (all-of-k, tau-bench) not just pass@1, and wire OpenTelemetry GenAI
  tracing through Langfuse or Arize Phoenix. Use when someone says "eval my agent", "is my agent
  reliable", "trace / observe the agent", "LLM as judge", "tool call accuracy", "trajectory eval",
  "pass^k / pass@k", "regression test for agents", "why did the agent do that", or "agent observability".
when_to_use:
  - "You built an agent and need to know if it actually works — measure success, not vibes"
  - "You want reliability, not luck: does it solve the same task on every one of k tries (pass^k)?"
  - "You need to grade whether the sequence of tool calls (the trajectory) was correct"
  - "You must choose between deterministic grading and an LLM-as-judge and wire one up"
  - "You want distributed traces of every LLM/tool span (Langfuse or Phoenix) to debug behaviour"
  - "You need a repeatable regression harness / dataset run to catch agent quality drift over releases"
when_not_to_use:
  - "You just want structured output from one LLM call — use instructor-structured-outputs or baml-structured-prompts"
  - "You're optimizing/compiling prompts against a metric — use dspy-program-optimization or prompt-optimization"
  - "You want a Swarm-specific test rig only — use swarm-evaluation-harness"
  - "You're defending against prompt injection / jailbreaks specifically — use llm-guardrails-injection-defense or swarm-guardrails"
  - "You need to build the agent itself — use openai-agents-sdk, pydantic-ai-typed-agents, langgraph-durable-workflows, or crewai-flows-orchestration"
keywords: [agent eval, agent evaluation, llm as judge, tool call accuracy, trajectory eval, pass^k, pass@k, pass hat k, tau-bench, tau2-bench, reliability, opentelemetry, otel genai, langfuse, arize phoenix, phoenix evals, llm_classify, tracing, observability, dataset run, regression test, agent observability]
similar_to: [swarm-evaluation-harness, dspy-program-optimization, prompt-optimization, openai-agents-sdk, langgraph-durable-workflows]
inputs_needed:
  - "The agent (a callable) and a labelled task set: inputs + expected final state or reference answer"
  - "Grading mode: deterministic (exact/final-state) where possible, else an LLM-as-judge with a rubric + judge model"
  - "Backend for tracing/experiments: Langfuse (keys) or Arize Phoenix (self-host/cloud), plus a judge model API key"
produces: A runnable eval + tracing harness (trajectory + tool-call scores, pass^k reliability, OTEL traces in Langfuse/Phoenix)
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agent Evals & Tracing

Agents are stochastic and multi-step, so a single "it worked once" tells you nothing. This skill sets
up **measurement** (trajectory + tool-call grading, deterministic vs LLM-as-judge, **pass^k**
reliability) and **observability** (OpenTelemetry GenAI spans in Langfuse or Arize Phoenix) so you can
prove an agent works and see *why* when it doesn't.

## When to use

Reach for this after you have a working agent and need a number you trust: a regression gate before
release, a reliability score for a flaky agent, or a trace to debug a weird tool call. Grounded
against **tau2-bench**, **Langfuse Python SDK v3/v4** (`get_client()`, OTEL-based), and
**arize-phoenix-evals**.

## Prerequisites

Pick the pieces you need — none of this is one monolith.

```bash
# Tracing + experiments (choose one backend, or run both)
pip install langfuse                      # v3/v4, OTEL-based; needs a Langfuse project (cloud or self-host)
pip install arize-phoenix arize-phoenix-otel arize-phoenix-evals   # local UI + OTEL + evaluators

# A benchmark harness for tool-agent-user tasks (optional, opinionated)
git clone https://github.com/sierra-research/tau2-bench && cd tau2-bench && uv sync
```

- **Judge model**: LLM-as-judge and Phoenix evaluators call a model — set `OPENAI_API_KEY` /
  `ANTHROPIC_API_KEY`. Prefer a *different, strong* model as judge than the one under test.
- **Langfuse**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`
  (`https://cloud.langfuse.com` EU, `https://us.cloud.langfuse.com` US, or your self-host URL).
- Honest note: deterministic grading needs **no** model or backend and is the cheapest, most stable
  signal. Reach for LLM-as-judge only when the correct answer is open-ended.

## Recipe 1 — Choose your grader (deterministic first)

Grade the **final state / outcome** whenever you can; fall back to a judge only for open-ended text.

```python
# Deterministic: cheap, zero variance, no API calls. Use for tool args, DB state, exact/JSON answers.
def grade_final_state(actual: dict, expected: dict) -> bool:
    return actual == expected          # or subset/JSON-diff; assert the WRITES the agent made

def grade_tool_calls(actual_calls: list[dict], required_calls: list[dict]) -> float:
    """Fraction of required (name, args) tool calls that appear in the trajectory."""
    hits = sum(1 for r in required_calls if r in actual_calls)
    return hits / len(required_calls) if required_calls else 1.0
```

This is exactly tau-bench's philosophy: it judges success on the **final world state** (the database
and required outputs vs an annotated goal), not the wording of the conversation.

## Recipe 2 — LLM-as-judge for trajectory & tool-call accuracy (Phoenix)

When the answer is open-ended, send the ordered trajectory to a judge model and get a labelled score.
`llm_classify` uses function calling to constrain the output to your `rails`, so parsing is reliable.

```python
import pandas as pd
from phoenix.evals import llm_classify, OpenAIModel

TRAJECTORY_PROMPT = """
You are grading an AI agent's TOOL-CALL TRAJECTORY.
[User goal]: {goal}
[Ordered tool calls the agent made]: {tool_calls}
Did the trajectory use the right tools, in a sensible order, with correct arguments,
and avoid unnecessary or destructive calls? Answer with a single word: correct or incorrect.
"""

df = pd.DataFrame([
    {"goal": "cancel order 42 then email the user",
     "tool_calls": "get_order(42) -> cancel_order(42) -> send_email(user, 'cancelled')"},
])

result = llm_classify(
    dataframe=df,
    template=TRAJECTORY_PROMPT,
    model=OpenAIModel(model="gpt-4.1"),      # the JUDGE model
    rails=["correct", "incorrect"],           # constrains output; anything else -> NaN
    provide_explanation=True,                 # free-text rationale for debugging
    concurrency=8,
)
print(result[["label", "explanation"]])
```

Use the same pattern with different templates for **tool-call correctness**, **relevance**,
**hallucination**, or a custom rubric. Keep judge prompts short, binary, and give a rubric — vague
judges are noisy. Always spot-check a sample of judge labels against your own reading.

## Recipe 3 — pass^k reliability (tau-bench), not pass@1

- **pass@k** = at least one of k tries succeeds (good for code where you can pick the winner).
- **pass^k** = *all* k tries succeed, averaged over tasks — the tau-bench headline. One flaky failure
  tanks it. Use when a single failure is costly (policy adherence, money movement) and the agent
  can't self-check. Unbiased per-task estimator from n trials with c successes: `C(c,k) / C(n,k)`.

Run multiple trials per task, then compute the curve with the bundled helper:

```bash
# Run tau2-bench itself (5 tasks, k=4 trials each):
tau2 run --domain airline --agent-llm gpt-4.1 --user-llm gpt-4.1 --num-trials 4 --num-tasks 5
tau2 view          # browse results in data/simulations/

# Or compute pass^k from YOUR OWN results (CSV task_id,success one row per trial, or JSON):
printf 'task_id,success\nt1,pass\nt1,pass\nt1,fail\nt2,pass\nt2,pass\nt2,pass\n' \
  | python3 scripts/pass_hat_k.py
# -> pass^1=0.8333  pass^2=0.6667  pass^3=0.5000  (watch it decay: that decay IS the reliability signal)
```

A high mean success rate with a collapsing pass^k means the agent is inconsistent — ship-blocking for
customer-facing agents even if pass^1 looks fine.

## Recipe 4 — Trace every span with OpenTelemetry (Langfuse)

Wrap the agent so each LLM/tool call is a nested OTEL span you can inspect and score. SDK v3/v4 is
OTEL-based, so spans auto-nest via context propagation and third-party OTEL instrumentation is captured.

```python
from langfuse import get_client, observe

langfuse = get_client()
assert langfuse.auth_check()               # fail fast on bad keys

@observe()                                  # creates a span; nested @observe calls auto-nest
def run_task(user_input: str) -> str:
    with langfuse.start_as_current_observation(as_type="generation", name="plan",
                                               model="gpt-4.1") as gen:
        answer = my_agent(user_input)        # your agent loop; its LLM/tool spans nest under here
        gen.update(input=user_input, output=answer)
    # Attach an eval score to THIS trace so grading lives next to the trace:
    langfuse.create_score(name="final_state_correct",
                          value=1.0 if grade_final_state(actual, expected) else 0.0,
                          data_type="NUMERIC", comment="deterministic")
    return answer

run_task("cancel my order")
langfuse.flush()                            # flush before the process exits or spans are lost
```

Phoenix equivalent for tracing: `from phoenix.otel import register; register(project_name="agent",
auto_instrument=True)` starts local OTEL collection you can view in the Phoenix UI. Both backends read
the OTEL **GenAI semantic conventions** (`gen_ai.*` span attributes), so any OTEL-instrumented library
(LangChain, OpenAI Agents SDK, etc.) shows up automatically.

## Recipe 5 — Regression harness on a dataset (Langfuse experiments)

Freeze a labelled dataset and re-run your agent + graders on every release to catch drift.

```python
task = langfuse.create_dataset_item(dataset_name="support-eval",
                                    input={"q": "cancel order 42"},
                                    expected_output={"order_status": "cancelled"})

def evaluator(*, input, output, expected_output, **_):
    return {"name": "correct", "value": float(output == expected_output)}

# run_experiment ties each item to a fresh trace + your evaluators; compare runs over time in the UI
langfuse.run_experiment(name="release-2026-07", dataset_name="support-eval",
                        task=lambda item: my_agent(item.input["q"]),
                        evaluators=[evaluator])
```

## Verify

- `python3 scripts/pass_hat_k.py` on the sample above prints `pass^1=0.8333 … pass^3=0.5000` — matches
  the hand computation, so the estimator is right.
- `langfuse.auth_check()` returns `True`; after a run, the trace appears in the Langfuse UI with nested
  spans and your `create_score` attached.
- `llm_classify(...)` returns a DataFrame whose `label` values are only your `rails` (never free text);
  any `NaN` label means the judge went off-script — tighten the prompt.
- Deterministic grades are byte-stable across re-runs; a judge grade that flips on re-run is a signal
  your rubric is too loose.

## Pitfalls

- **pass@1 flatters flaky agents.** Report pass^k (k≥3–5) for anything customer-facing; a good mean with
  collapsing pass^k is a red flag, not a pass.
- **Judge = same model as agent** → correlated blind spots and grade inflation. Use a different, strong
  judge and validate it against human labels on a sample before trusting it.
- **Grading the transcript instead of the outcome.** Prefer final-state/tool-arg checks (tau-bench style);
  conversations can sound perfect while the DB write was wrong.
- **Too few trials.** pass^k needs multiple trials per task (n ≥ k). One run per task gives you nothing
  about reliability.
- **Forgetting `langfuse.flush()`** (or letting the process die) drops spans — OTEL export is async.
- **Unbounded LLM-judge cost.** Judges are LLM calls; cap `concurrency`, sample, and cache. Reserve them
  for genuinely open-ended answers — deterministic checks are free and never flake.
- **Non-deterministic "deterministic" checks.** Normalise whitespace/ordering/JSON key order before
  exact-match, or your baseline grader will flap.

## Sources

- tau2-bench: https://github.com/sierra-research/tau2-bench · pass^k: https://www.philschmid.de/agents-pass-at-k-pass-power-k
- Langfuse OTEL SDK: https://langfuse.com/docs/observability/sdk/overview
- Arize Phoenix evals: https://arize.com/docs/phoenix/evaluation/llm-evals · https://pypi.org/project/arize-phoenix-evals/
