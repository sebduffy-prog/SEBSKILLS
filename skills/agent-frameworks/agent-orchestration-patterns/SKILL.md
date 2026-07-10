---
name: agent-orchestration-patterns
category: agent-frameworks
description: >
  Framework-agnostic reference and decision heuristics for the canonical multi-agent
  topologies — prompt chaining, routing/classifier, parallel fan-out (sectioning & voting),
  orchestrator-worker / manager-supervisor, evaluator-optimizer, and hub-and-spoke vs mesh
  swarm handoffs. Use when the user asks "which agent pattern should I use", "single agent
  vs multi-agent", "orchestrator vs swarm", "how do I structure my agents", "fan out to
  subagents", "manager pattern", or wants to pick a topology BEFORE committing to LangGraph,
  CrewAI, or the OpenAI Agents SDK. Grounded in Anthropic's Building Effective Agents and
  OpenAI's Practical Guide to Building Agents.
when_to_use:
  - "User is deciding how to structure a multi-step LLM system and hasn't picked a framework yet"
  - "Asking 'single agent or multi-agent?' or 'do I even need agents or just a workflow?'"
  - "Choosing between orchestrator-worker (manager) and decentralized handoff (swarm) topologies"
  - "Wants to add self-correction (evaluator-optimizer) or parallel voting to improve quality"
  - "Needs a routing/triage layer to send requests to specialised sub-agents"
  - "Reviewing an over-engineered agent design and wants the simplest topology that works"
when_not_to_use:
  - "Ready to build in a specific framework → langgraph-durable-workflows, crewai-flows-orchestration, openai-agents-sdk, or pydantic-ai-typed-agents"
  - "Implementing handoff/router/swarm in code specifically → handoff-router-swarm"
  - "Building a single classifier/triage agent → classifier-agent-routing"
  - "Adding guardrails or injection defense → swarm-guardrails, llm-guardrails-injection-defense"
  - "Optimizing a single prompt or DSPy program, not topology → prompt-optimization, dspy-program-optimization"
keywords: [agent orchestration, multi-agent, multi agent, orchestrator-worker, manager pattern, supervisor, swarm, handoff, hub and spoke, mesh, prompt chaining, routing, classifier, router, parallelization, fan-out, fanout, sectioning, voting, evaluator-optimizer, reflection, single agent vs multi agent, agent topology, workflow vs agent, decision heuristics]
similar_to: [handoff-router-swarm, classifier-agent-routing, langgraph-durable-workflows, crewai-flows-orchestration, openai-agents-sdk]
inputs_needed:
  - "The task: is it one bounded job, or does it decompose into distinct sub-tasks / tools?"
  - "Is the sub-task structure known ahead of time (fixed) or discovered at runtime (dynamic)?"
  - "Quality bar: does output need iterative self-correction or a verifiable check?"
  - "Latency & cost budget (parallel & multi-agent cost more tokens; chaining adds latency)"
produces: A chosen topology + rationale you can hand to a framework skill to implement.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agent Orchestration Patterns

A topology chooser. Pick the **simplest** structure that meets the quality bar, then hand it to
a framework skill to build. Core rule from Anthropic's *Building Effective Agents*: prefer a
**workflow** (LLMs on predefined code paths) over an **agent** (LLM dynamically directs its own
steps/tools) unless the task genuinely needs open-ended, unpredictable steps. Every added
agent, hop, or parallel branch buys capability at the cost of tokens, latency, and failure modes.

## When to use

- Before writing any orchestration code — decide topology first.
- When a design feels over-built (too many agents) or under-built (one prompt doing everything).
- To justify single-agent vs multi-agent to a stakeholder.

## Prerequisites

None — this is a reference + heuristic. No install, no keys. You'll implement the chosen pattern
in a framework skill (LangGraph / CrewAI / OpenAI Agents SDK / Pydantic AI) afterward.

## The decision ladder (stop at the first that fits)

1. **Single prompt** (+ retrieval/tools) — one bounded task, one call. Most tasks. Start here.
2. **Prompt chaining** — task splits into a *fixed* sequence; each step's output feeds the next,
   with a programmatic gate/check between. Trades latency for accuracy on decomposable tasks.
3. **Routing** — inputs fall into distinct classes needing different handling. A cheap classifier
   picks the branch; each branch gets a specialised prompt/tool set.
4. **Parallelization** — independent sub-tasks (**sectioning**) or repeated attempts for
   confidence (**voting**) run concurrently, then a reducer merges. Cuts latency; raises quality.
5. **Orchestrator-workers (manager/supervisor)** — sub-tasks are *not* known upfront; a central
   LLM decomposes at runtime, delegates to workers, and synthesizes. Central control & memory.
6. **Evaluator-optimizer (reflection)** — a generator LLM proposes, an evaluator LLM critiques
   against criteria, loop until it passes or a max-iteration cap. Use when good criteria exist
   and iteration measurably helps.
7. **Autonomous agent** — open-ended goal, unpredictable step count, LLM drives its own tool loop
   with environment feedback and human checkpoints. Highest capability, hardest to control.

If steps 1–4 (workflows) suffice, **do not** reach for 5–7 (agents).

## Recipes (topology sketches — pseudocode, framework-agnostic)

### Prompt chaining
```
draft   = llm(step1_prompt, input)
if not gate(draft): return fail_fast(draft)     # programmatic checkpoint
polished = llm(step2_prompt, draft)
return   llm(step3_prompt, polished)
```
Good for: write→translate, outline→draft→edit, extract→validate→format.

### Routing / classifier triage
```
route = classify(input)            # cheap/fast model, closed set of labels + "other"
return {
  "refund":  refund_agent,
  "billing": billing_agent,
  "tech":    tech_agent,
}.get(route, fallback_agent)(input)
```
Keep the label set closed; always include a fallback. See `classifier-agent-routing`.

### Parallel — sectioning (independent subtasks)
```
parts   = [llm(p, input) for p in [summary_p, risks_p, actions_p]]  # run concurrently
return reduce(combine_prompt, parts)                                # merge/synthesize
```

### Parallel — voting (confidence / self-consistency)
```
votes  = [llm(prompt, input, temperature=0.8) for _ in range(N)]    # concurrent
return majority(votes)   # or: escalate to human if no consensus
```
Voting is also a cheap guardrail: run the same safety check N times, act only on agreement.

### Orchestrator-workers (manager / supervisor)
```
plan    = orchestrator.decompose(goal)          # subtasks discovered at runtime
results = [worker(sub) for sub in plan.subtasks] # fan out (parallel or sequential)
return   orchestrator.synthesize(goal, results)
```
Manager holds the shared context; workers are stateless & specialised. OpenAI calls this the
**manager pattern**; frameworks call it supervisor. Central control, easy to reason about, but
the manager is a bottleneck and a single point of failure.

### Evaluator-optimizer (reflection loop)
```
out = generator(task)
for _ in range(MAX_ITERS):                # ALWAYS cap iterations
    verdict = evaluator(out, criteria)    # returns pass | actionable feedback
    if verdict.passed: break
    out = generator(task, feedback=verdict.feedback)
return out
```
Only worthwhile when the evaluator gives *actionable* feedback and iteration actually improves
results (e.g. code that must compile, translations judged against a rubric).

## Hub-and-spoke vs mesh (multi-agent control)

Two ways multiple agents coordinate — the key axis is *who decides what happens next*:

| | Hub-and-spoke (centralized) | Mesh / swarm (decentralized) |
|---|---|---|
| Control | Orchestrator/manager routes every step | Peers **hand off** control to each other |
| Context | Manager owns shared state | Context travels with the handoff |
| Pros | Predictable, observable, easy to debug | Flexible, no bottleneck, agents own their domain |
| Cons | Manager is a bottleneck & SPOF; token-heavy | Loops/ping-pong, harder to trace, drift |
| Best when | Sub-tasks fan out from one goal | Peer specialists pass a conversation along |
| Frameworks | LangGraph supervisor, OpenAI manager | OpenAI/`Swarm` handoffs, `handoff-router-swarm` |

Default to **hub-and-spoke** first (it's easier to observe and evaluate). Move to mesh handoffs
only when a central manager becomes the bottleneck or when domains are cleanly separable and a
conversation naturally flows between specialists. Cap handoff depth to prevent ping-pong.

## Guardrails & observability (any topology)

- **Guardrails** run *alongside* the topology, not as a stage: input filters (PII, injection,
  off-topic), output checks (schema, safety), and tool-call approval for high-risk actions. See
  `swarm-guardrails` and `llm-guardrails-injection-defense`.
- **Trace everything**: every hop, tool call, and handoff. Multi-agent bugs are invisible without
  traces — see `agent-evals-and-tracing`.
- **Cap all loops** (evaluator iterations, handoff depth, agent steps) and set a token/time budget.
- **Human checkpoints** on irreversible actions in autonomous agents.

## Verify

Sanity-check the chosen topology against these:

- [ ] Could a **single prompt + tools** do this? If yes, don't add agents.
- [ ] Is sub-task structure **fixed** (workflow: chain/route/parallel) or **dynamic**
      (agent: orchestrator/autonomous)? Match accordingly.
- [ ] Does quality need **iteration with a real check**? Only then add evaluator-optimizer.
- [ ] Every loop has a **max-iteration / max-depth cap**.
- [ ] There's a **fallback branch** for unroutable / failed inputs.
- [ ] You can **trace** every hop and you've set a **token/latency budget**.
- [ ] Chosen hub-and-spoke unless a manager bottleneck justifies mesh.

## Pitfalls

- **Multi-agent by default.** The most common mistake. Start single-agent; split only when one
  agent's prompt/tools become unmanageable or a genuine bottleneck appears.
- **Agent where a workflow works.** If steps are predictable, hard-code the path — cheaper, faster,
  more reliable than letting an LLM re-derive the plan every run.
- **Uncapped reflection loops** — evaluator-optimizer without a cap can loop forever or oscillate;
  it also doesn't help if the evaluator's feedback isn't actionable.
- **Swarm ping-pong** — agents hand back and forth without progress. Add depth caps and a
  terminal/answer agent.
- **Parallel token blowup** — voting with large N or wide fan-out multiplies cost; size N to the
  actual confidence you need.
- **Open-ended router labels** — classifiers drift without a closed label set + explicit "other".
- **No shared-state discipline in hub-and-spoke** — the manager becomes a giant context blob; keep
  workers stateless and pass only what each needs.

## Sources

- Anthropic — *Building Effective Agents* (workflows vs agents; chaining, routing,
  parallelization, orchestrator-workers, evaluator-optimizer).
- OpenAI — *A Practical Guide to Building Agents* (single vs multi-agent; manager vs
  decentralized/handoff patterns; guardrails).
