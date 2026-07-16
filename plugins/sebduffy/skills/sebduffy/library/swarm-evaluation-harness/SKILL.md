---
name: swarm-evaluation-harness
category: agent-frameworks
description: >
  Evaluate multi-agent swarms at the TRAJECTORY level, not just the final answer — score handoff/routing
  correctness, per-agent sub-goal (task) completion, tool-call correctness, plan quality/adherence, step
  efficiency, and attribute cost/latency/tokens to each sub-agent. Uses DeepEval @observe spans + agent
  metrics with an evals_iterator or pytest harness. Use when asked to "eval my agent swarm", "test the
  handoff router", "did the right sub-agent get called", "measure per-agent cost", "trajectory eval",
  "why did the multi-agent run fail", or to build a CI regression suite for an orchestrator/handoff system.
when_to_use:
  - "You have a multi-agent / swarm / handoff system and want to know WHICH agent failed, not just that the final answer was wrong"
  - "You need to verify the router/orchestrator handed off to the correct specialist sub-agent"
  - "You want per-agent cost, latency and token attribution across a trajectory"
  - "You want a CI regression suite that fails the build when handoff correctness or task completion drops"
  - "You need trajectory-level metrics: plan quality, plan adherence, tool correctness, step efficiency"
  - "A swarm run 'worked' but you suspect wasted steps, wrong tool args, or a mis-route"
when_not_to_use:
  - "Building the swarm itself (routing/handoff logic) — use handoff-router-swarm or agent-orchestration-patterns"
  - "General single-agent tracing/observability without pass/fail metrics — use agent-evals-and-tracing"
  - "Blocking unsafe tool calls / injection at runtime — use swarm-guardrails or llm-guardrails-injection-defense"
  - "Optimizing a single prompt or DSPy program — use prompt-optimization or dspy-program-optimization"
  - "Classifier-only routing accuracy on a labeled set — use classifier-agent-routing"
keywords: [deepeval, multi-agent eval, swarm evaluation, trajectory eval, handoff correctness, sub-goal completion, task completion metric, tool correctness, plan adherence, step efficiency, agent spans, per-agent cost, latency attribution, confident-ai, agent regression test, orchestrator eval, mult-agent, evals_iterator]
similar_to: [agent-evals-and-tracing, handoff-router-swarm, classifier-agent-routing, agent-orchestration-patterns, swarm-guardrails]
inputs_needed:
  - The swarm's Python entrypoint and each sub-agent function (so they can be wrapped with @observe)
  - A small dataset of goldens (input + optional expected_tools / expected sub-agent) to eval against
  - Which layer(s) matter: routing/handoff, task completion, tool correctness, plan, efficiency, cost
produces: A DeepEval trajectory-eval harness (dataset + span-attached metrics + evals_iterator/pytest runner) plus a per-agent cost/latency/handoff attribution report
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Swarm Evaluation Harness (trajectory-level multi-agent evals)

Evaluate a multi-agent system by its **trajectory** — the plan, the routing/handoffs, each sub-agent's
tool calls and sub-goal completion — instead of only the final string. Built on DeepEval's `@observe`
tracing + agent metrics. Grounded on the DeepEval agent-eval docs and the *Evaluation and Benchmarking of
LLM Agents* survey (arXiv:2507.21504), whose taxonomy separates **what** to evaluate (behaviour,
capability, reliability) from **how** (per-step vs end-to-end).

## When to use
Multi-agent run failed or feels wasteful and you need to localise the fault to a specific agent, verify
the router chose the right specialist, or gate a CI build on handoff correctness + task completion. If you
only need traces (no pass/fail), use `agent-evals-and-tracing`.

## Prerequisites
- `pip install -U deepeval` (Python 3.9+). Metrics that use an LLM judge need a key: `export OPENAI_API_KEY=...`
  (or configure a custom judge model — see DeepEval "using a custom LLM").
- `ToolCorrectnessMetric` and `StepEfficiencyMetric` are **deterministic** (no LLM/key). `TaskCompletionMetric`,
  `PlanQualityMetric`, `PlanAdherenceMetric`, `ArgumentCorrectnessMetric` use a judge model.
- Optional `deepeval login` pushes results to the Confident AI dashboard; everything below runs fully local.
- Auto token/cost capture on LLM spans requires patching your client, e.g. `trace_manager.configure(openai_client=client)`.

## The metric layers (attach at the right scope)
| Layer | Metric | Scope | Judge? |
|---|---|---|---|
| Reasoning | `PlanQualityMetric`, `PlanAdherenceMetric` | full trace (`evals_iterator`) | yes |
| Action | `ToolCorrectnessMetric`, `ArgumentCorrectnessMetric` | the specific span (`@observe`) | tool=no, arg=yes |
| Execution | `TaskCompletionMetric`, `StepEfficiencyMetric` | full trace / per agent span | task=yes, step=no |

Rule of thumb: **execution + reasoning metrics need the whole trace → attach via `evals_iterator(metrics=[...])`;
action metrics judge one decision → attach via `@observe(metrics=[...])` on that component.**

## Recipe 1 — instrument the swarm with agent spans
Wrap the orchestrator and each sub-agent. `@observe` uses a `ContextVar` call stack, so nested sub-agent
calls **auto-nest** into a correct execution tree — a handoff is just one agent span calling another.

```python
from deepeval.tracing import observe, update_current_span, update_current_trace
from deepeval.metrics import TaskCompletionMetric, ToolCorrectnessMetric
from deepeval.test_case import ToolCall

@observe(type="agent", name="weather_specialist", metrics=[TaskCompletionMetric()])
def weather_agent(query: str) -> str:
    result = call_weather_api(query)                      # a @observe(type="tool") fn
    update_current_span(tools_called=[ToolCall(name="get_weather")])
    return result

@observe(type="agent", name="router")                    # the orchestrator / handoff root
def swarm(query: str) -> str:
    target = route(query)                                 # your routing/handoff logic
    answer = weather_agent(query) if target == "weather" else general_agent(query)
    update_current_trace(input=query, output=answer)      # sets the trace-level test case
    return answer
```

## Recipe 2 — routing / handoff correctness
Handoff = "did the router invoke the correct sub-agent for this input?" Model it as a tool-correctness
problem on the router span: treat each dispatch as a `ToolCall(name=<sub_agent_name>)`.

```python
@observe(type="agent", name="router", metrics=[ToolCorrectnessMetric()])
def router(query: str):
    chosen = route(query)                                 # e.g. "billing_agent"
    update_current_span(
        tools_called=[ToolCall(name=chosen)],
        expected_tools=[ToolCall(name=get_current_golden().expected_tools[0].name)],
    )
    return dispatch(chosen, query)
```
`ToolCorrectnessMetric` is deterministic: exact-match on tool name (and, with `should_consider_ordering`/
`should_exact_match`, on order and args). A mis-route scores 0 and names the wrong agent in `.reason`.

## Recipe 3 — the dataset + runner
Build goldens once; attach whole-trace metrics on the iterator. Each loop iteration runs your swarm and
DeepEval binds the emitted trace to that golden.

```python
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import TaskCompletionMetric, StepEfficiencyMetric, PlanAdherenceMetric
from deepeval.test_case import ToolCall

dataset = EvaluationDataset(goldens=[
    Golden(input="What's the weather in Paris tomorrow?",
           expected_tools=[ToolCall(name="weather_specialist")]),
    Golden(input="Refund my last order",
           expected_tools=[ToolCall(name="billing_agent")]),
])

for golden in dataset.evals_iterator(
    metrics=[TaskCompletionMetric(), StepEfficiencyMetric(), PlanAdherenceMetric()],
):
    swarm(golden.input)          # emits the trace; per-span metrics (Recipe 2) also fire
```

Isolate one sub-agent: attach the metric to *its* agent span (Recipe 1) — DeepEval scores it on every run
in which it is invoked, so a specialist that's only reached via handoff still gets evaluated in isolation.

## Recipe 4 — CI regression gate (pytest)
```python
import pytest
from deepeval import assert_test
from deepeval.dataset import EvaluationDataset, Golden
from deepeval.metrics import ToolCorrectnessMetric, TaskCompletionMetric

dataset = EvaluationDataset(goldens=[...])

@pytest.mark.parametrize("golden", dataset.goldens)
def test_swarm(golden: Golden):
    swarm(golden.input)
    assert_test(golden=golden, metrics=[ToolCorrectnessMetric(), TaskCompletionMetric()])
```
Run: `deepeval test run test_swarm.py`. Non-passing metrics fail the build; use `--repeat 3` to flag flaky routes.

## Recipe 5 — per-agent cost / latency / handoff attribution
Docs-native attribution lives in the Confident AI trace view. For a self-contained rollup (CI artifact,
no dashboard), export spans to a flat list and run the bundled helper:

```bash
# spans.json: [{"span_id","parent_id","agent","type","cost_usd","latency_ms"}, ...]
python3 scripts/agent_attribution.py spans.json
```
It emits each agent's span count, total + % of cost, summed latency, and the handoff edge list (a child
span whose `agent` differs from its parent's = one handoff). Use it to spot the agent burning 60% of spend
or a router looping the same specialist. It is framework-agnostic — feed it spans from DeepEval, OTel, or
your own logger; it never invents fields.

## Framework note (OpenAI Agents SDK)
Using the OpenAI Agents integration, attach metrics per sub-agent directly: `Agent(name="weather_specialist",
..., agent_metrics=[TaskCompletionMetric()])`, and DeepEval scores each agent on the run in which the
orchestrator hands off to it. Same three metric layers apply.

## Verify
- `python3 scripts/agent_attribution.py <(echo '[{"span_id":"a","parent_id":null,"agent":"router","cost_usd":0.01}]')` prints a rollup.
- A deliberately mis-routed golden makes `ToolCorrectnessMetric` score 0 and its `.reason` name the wrong agent.
- `deepeval test run` exits non-zero when any attached metric is below threshold.
- The Confident AI (or `evals_iterator` printed) trace tree shows sub-agent spans nested under the router.

## Pitfalls
- **Judge non-determinism:** LLM-judged metrics (task/plan/argument) vary run-to-run — set explicit
  `threshold=`, use `--repeat`, and pin the judge model; don't gate CI on a single noisy run.
- **Wrong scope:** attaching `ToolCorrectnessMetric` to the trace instead of the emitting span, or a
  whole-trace metric to a leaf span, either no-ops or scores the wrong thing. Follow the layer table.
- **Missing `update_current_span`/`update_current_trace`:** without setting `tools_called`/`expected_tools`
  or trace `input/output`, action and completion metrics have nothing to score.
- **Cost/tokens blank:** LLM cost/token capture needs client patching (`trace_manager.configure(...)`); a
  raw un-patched call records latency only. The helper defaults missing `cost_usd`/`latency_ms` to 0.
- **Final-answer myopia:** a correct final string can hide a wrong handoff + a self-correcting retry.
  Always keep at least one routing (tool-correctness) and one efficiency metric in the suite.
- **Dataset drift:** update goldens' `expected_tools` when you rename/add a sub-agent, or every route
  silently "fails".

Sources: [DeepEval agent quickstart](https://deepeval.com/docs/getting-started-agents) ·
[Agent metrics guide](https://deepeval.com/guides/guides-ai-agent-evaluation-metrics) ·
[Tracing agents](https://deepeval.com/guides/guides-tracing-ai-agents) ·
[LLM Agent Evaluation survey, arXiv:2507.21504](https://arxiv.org/abs/2507.21504)
