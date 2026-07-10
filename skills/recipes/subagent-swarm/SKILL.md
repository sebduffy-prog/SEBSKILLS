---
name: subagent-swarm
category: recipes
description: >
  Recreate a portable agent-orchestration harness — the kind sold as a marketplace product (wshobson's
  agent marketplace, the openai-agents "handoff swarm" starter) — by CHAINING four existing library skills
  instead of buying a bundle. Pick a topology, wire peer-to-peer handoffs, add fail-fast tripwires,
  gate it behind a trajectory-eval CI suite. Pure orchestration over any LLM. Use when the
  user wants a "subagent swarm", "agent orchestration harness", "multi-agent framework", "wshobson agents",
  "openai swarm clone", or a reusable specialist-handoff system they own end to end.
when_to_use:
  - User wants a reusable multi-agent orchestration harness they own, not a one-off script or a paid bundle
  - User references a marketplace/starter (wshobson agents, openai-agents swarm) and wants to rebuild it locally
  - User needs specialists that hand control to each other AND safety tripwires AND a regression eval, together
  - User is standing up a customer-support / research / triage swarm and wants topology + handoffs + guardrails + evals in one pass
  - User wants the combo to be provider-agnostic (works on OpenAI, Anthropic, or local models)
when_not_to_use:
  - User only needs to pick a topology and hasn't built anything → agent-orchestration-patterns alone
  - User only needs the peer-to-peer handoff wiring → handoff-router-swarm (or openai-agents-sdk) alone
  - User only needs input/output safety on an existing app → swarm-guardrails alone
  - User only needs to eval an already-built swarm → swarm-evaluation-harness alone
  - User wants one central router with no specialist-to-specialist transfer → classifier-agent-routing
keywords: [subagent swarm, agent orchestration harness, multi-agent framework, wshobson agents, openai-agents, agent marketplace, handoff swarm, specialist agents, orchestrator, guardrails, trajectory eval, portable harness, peer-to-peer handoff, agent combo, recipe, decentralized agents]
similar_to: [agent-orchestration-patterns, handoff-router-swarm, openai-agents-sdk, swarm-guardrails, swarm-evaluation-harness]
inputs_needed:
  - The task domain and the set of specialist roles you want (e.g. triage, billing, research, code-writer)
  - Model + SDK choice per agent (OpenAI Agents SDK, langgraph-swarm, or provider-agnostic)
  - A handful of goldens (representative inputs + expected route/handoff/tools) for the eval gate
  - Any safety policy the swarm must enforce (jailbreak block, PII scrub, off-topic, tool allowlist)
produces: A self-owned subagent-swarm harness — a chosen topology, peer-to-peer handoff wiring, fail-fast input/output guardrails, and a trajectory-level eval CI suite that gates changes
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Subagent Swarm (portable agent-orchestration harness)

Stand up your own multi-agent orchestration harness by chaining four skills the library already ships —
no marketplace bundle, no vendored framework you can't see inside. You end up with a swarm of specialists
that hand control to each other, refuse unsafe input/output, and can't regress silently because a
trajectory eval gates every change.

## What it recreates

The class of product sold as a ready-made **agent orchestration harness**:

- **wshobson's agent marketplace** — a curated pack of role-specialist subagents you drop into a project.
- **the openai-agents "handoff swarm" starter** — triage agent + specialists that `transfer_to_*` each other.
- more broadly, any "buy our multi-agent framework" bundle (CrewAI-style crews, Swarm clones).

What those give you is: a topology, handoff plumbing, some safety rails, and (sometimes) a test harness.
This recipe reproduces all four from primitives you already own, so nothing is a black box.

## Feasibility

**Green — fully reproducible locally.** This is pure orchestration logic layered over whatever LLM you
already call; there is no proprietary model, hosted service, or GPU in the critical path. The only external
dependency is the same LLM API you were going to use anyway (OpenAI, Anthropic, or a local model) — that is
not an amber step, it's the substrate every option assumes. Every wiring, safety, and eval concern is code
you run and inspect. Nothing here needs a paid marketplace license.

## The combo

An ordered chain of four existing sibling skills. Run them in sequence; each consumes the last one's output.

1. **`agent-orchestration-patterns`** — *pick the topology.* Decide, before writing any wiring, whether you
   want decentralized peer handoffs (swarm), a central orchestrator-worker (manager), or a routing/triage
   layer. This is the design gate: it stops you from over-building. Output = a named topology + the specialist
   roster.
2. **`handoff-router-swarm`** (or **`openai-agents-sdk`** if you want the full SDK surface) — *wire the
   handoffs.* Implement the topology from step 1 as peer-to-peer transfers: `transfer_to_*` tools with the
   active agent tracked in shared state so the conversation resumes with whoever was last active. Use
   `openai-agents-sdk` instead when you also want its built-in Sessions memory and Tracing in the same object
   model. Output = a runnable swarm entrypoint.
3. **`swarm-guardrails`** — *add fail-fast tripwires.* Wrap the swarm's inputs and outputs so a tripwire HALTS
   the run before tokens or side-effects are spent — jailbreak/injection block, PII scrub/detect, off-topic
   and NSFW output checks, tool/URL allowlisting. Output = the swarm from step 2, now safety-gated.
4. **`swarm-evaluation-harness`** — *gate it with trajectory evals.* Score the guarded swarm at the trajectory
   level: handoff/routing correctness, per-agent sub-goal completion, tool-call correctness, plan adherence,
   step efficiency, and per-agent cost/latency. Wire it into CI so the build fails when routing correctness or
   task completion drops. Output = a regression suite the harness ships with.

## Prerequisites

- Python 3.10+ (or TypeScript if you go the `openai-agents-sdk` TS route).
- One LLM API key (OpenAI, Anthropic, or a local endpoint) — the same one you already use.
- The four sibling skills above are invokable via `/sebduffy` so this recipe can chain to each.
- For step 4, DeepEval installed (the eval harness skill pins it) and a small goldens file.

## Run it

Do these in order; do not skip step 1 — picking the wrong topology is the most expensive mistake.

1. **Design.** Invoke `agent-orchestration-patterns`. Describe the domain and specialist roles from
   `inputs_needed`. Come away with a single named topology and a roster (e.g. `triage → {billing, refunds,
   escalation}` as a hub-and-spoke swarm). Write the roster down — it's the contract for step 2.
2. **Wire.** Invoke `handoff-router-swarm` (default) or `openai-agents-sdk` (if you want Sessions + Tracing).
   Implement each roster role as an agent and add `transfer_to_*` handoff tools per the topology. Confirm the
   active agent persists across turns in shared state. You now have a runnable swarm — smoke-test one happy
   path before adding safety.
3. **Guard.** Invoke `swarm-guardrails`. Attach input guardrails (jailbreak, PII, off-topic) and output
   guardrails (NSFW, hallucination, tool/URL allowlist) around the swarm entrypoint from step 2. Verify a
   deliberately bad input trips the wire and aborts *before* any specialist runs.
4. **Eval + gate.** Invoke `swarm-evaluation-harness`. Feed it your goldens (input + expected route/handoff/
   tools). Wrap each sub-agent with the harness's spans, run the `evals_iterator`/pytest suite, and add it to
   CI so a mis-route or dropped sub-goal fails the build.
5. **Package.** Freeze the four outputs as one repo: `agents/` (roster + handoffs), `guardrails/` (config +
   client), `evals/` (goldens + suite), and a README naming the chosen topology. That repo *is* your portable
   harness.

## Verify

- **Topology is deliberate:** the README names one topology and says why the simpler option was rejected.
- **Handoffs persist:** a two-turn conversation resumes with the last-active agent, not the entry agent.
- **Tripwires fire pre-spend:** a jailbreak/PII input aborts the run with zero specialist tokens spent
  (check the trace — no downstream agent executed).
- **Evals localize faults:** deliberately break one handoff edge; the eval suite fails on *that* agent's
  routing metric, not just "final answer wrong".
- **CI blocks regressions:** the eval suite is a required check and goes red when routing correctness or task
  completion drops below threshold.

## Pitfalls

- **Skipping step 1.** Jumping straight to handoffs and building a swarm when a single router (or no agents at
  all) would do is the #1 way to recreate the bloat these bundles are criticized for. Let
  `agent-orchestration-patterns` talk you *down* a level when it can.
- **Guardrails only on input.** Injection often lands in *output* (a specialist leaks PII or an off-policy
  URL). Guard both sides in step 3, or the tripwire is theatre.
- **Final-answer-only evals.** If step 4 scores only the last string, a swarm that reached the right answer
  via the wrong (expensive, mis-routed) trajectory passes. Score the trajectory — that's the whole point of
  `swarm-evaluation-harness`.
- **SDK lock-in creep.** Picking `openai-agents-sdk` in step 2 is fine, but keep the guardrail and eval layers
  provider-agnostic so the harness isn't welded to one vendor — that's what separates this from the bundle you
  chose not to buy.
- **No shared-state discipline.** Peer handoffs rely on the active-agent field in shared state; if two agents
  both think they're active you get ping-pong loops. Verify the single-writer invariant in step 2.
- **Treating the four outputs as separate projects.** The value is the *packaged* harness (step 5). Four loose
  scripts is not a portable harness — it's homework.
