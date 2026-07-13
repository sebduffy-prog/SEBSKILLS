---
name: managed-agents-outcomes
category: building-agents
description: >
  Turn eval from an offline afterthought into a per-session go/no-go by wiring
  Anthropic Managed Agents' rubric-based Outcomes as an in-loop delivery gate.
  You write a Markdown rubric of independently gradeable criteria, send a
  `user.define_outcome` event, and a SEPARATE grader agent (fresh context) scores
  each iteration and feeds per-criterion gaps back so the agent only ships when
  every criterion is satisfied — else it revises, hits the iteration cap, or
  fails. Use when someone wants an agent whose output must clear a bar before it
  ships (a deck, a model, a report), self-verifying agents, rubric grading, or an
  automated "don't hand this over until it's right" quality gate.
when_to_use:
  - "You want an agent's deliverable (deck, spreadsheet model, report, brief) blocked from shipping until it clears an explicit quality bar"
  - "You're on the Managed Agents API and want a grader-in-the-loop instead of an offline eval you run after the fact"
  - "You need an independent, unbiased second agent to judge output against criteria the first agent can't grade its own way around"
  - "You want automatic revise-on-fail: the grader pinpoints gaps and the agent takes another pass, up to a cap"
  - "You're wiring a per-session go/no-go signal (satisfied vs needs_revision vs failed) into a downstream pipeline or webhook"
when_not_to_use:
  - "You want an agent to improve its own prompt/skills across many sessions from run history — use auto-dream-loop instead"
  - "You're on the plain Messages API (single call / tool loop), not Managed Agents sessions — use claude-api and grade offline"
  - "You want to build the grader as a generic MCP tool rather than a native Outcomes grader — use mcp-builder"
  - "You need multi-agent decomposition (lead delegates to specialists), not a quality gate — use claude-code-agent-teams"
keywords:
  - managed-agents
  - outcomes
  - rubric
  - grader
  - define_outcome
  - eval-gate
  - self-verifying-agent
  - quality-gate
  - anthropic-api
  - go-no-go
  - span-outcome-evaluation
  - max-iterations
  - beta-header
  - claude-sessions
similar_to:
  - auto-dream-loop
  - claude-api
  - claude-code-agent-teams
  - permanent-agent
inputs_needed: >
  An Anthropic API key with Managed Agents beta access; a created agent (model +
  tools); a task description; and a Markdown rubric of explicit, independently
  gradeable criteria for the deliverable.
produces: >
  A running Managed Agents session that iterates under a grader until its output
  clears the rubric, plus a terminal go/no-go result (satisfied / failed /
  max_iterations_reached) and per-criterion grader feedback you can log or gate on.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Managed Agents Outcomes — Rubric Grading as a Delivery Gate

## When to use

You have a Managed Agents agent that produces a deliverable an agency actually
hands over — a pitch deck, a media plan spreadsheet, a DCF, an audience brief —
and "the model finished" is NOT the same as "this is good enough to send." Outcomes
makes *done* explicit: a separate grader agent scores every draft against your
rubric and refuses to let the loop end until every criterion passes. This turns
your eval from something you run offline next week into a per-session go/no-go the
agent enforces on itself before anything leaves the room.

Reach for this over hand-rolled "ask the model to check itself" because the grader
runs in a **fresh context window** with only the rubric and the artifact — it can't
rationalise its own earlier reasoning, which is the whole point.

## Prerequisites (read the honesty section)

- **Managed Agents is a distinct product from the Messages API.** Agents are
  server-managed, stateful, and have a hosted workspace/filesystem. Outcomes only
  exists inside a Managed Agents *session* — you cannot bolt it onto a plain
  `messages.create` call.
- **Beta, and moving.** Outcomes went to public beta on 2026-05-06 behind the beta
  header `managed-agents-2026-04-01`. It needs NO separate access request (unlike
  Dreaming). Because it is beta, exact event names, field names, and `result`
  values here MAY change — re-verify against the current cookbook
  (`platform.claude.com/cookbook/managed-agents-cma-verify-with-outcome-grader`)
  and `anthropics/skills` before you depend on a string in production.
- **SDK version.** You need a recent `anthropic` Python (or TS) SDK that exposes
  `client.beta.agents`, `client.beta.sessions`, and `sessions.events`. The SDK
  sets `managed-agents-2026-04-01` automatically on `client.beta.{agents,sessions,...}`
  calls, but passing `betas=[...]` explicitly is safe and self-documenting.
- **Cost.** The grader is a full extra agent invocation per iteration, same model
  and tools as the writer. A 5-iteration run can be ~2x the token cost of an
  ungraded run. Anthropic's published wins for the trade: ~8.4% quality lift on
  Word docs, ~10.1% on PowerPoint versus standard prompting.
- macOS note: this Mac's `python3` is 3.9; the modern `anthropic` SDK is fine on
  3.9 but confirm with `python3 -c "import anthropic"`.

## Recipe 1 — Minimal delivery gate

```python
import anthropic

client = anthropic.Anthropic()          # ANTHROPIC_API_KEY in env
BETAS = ["managed-agents-2026-04-01"]
MODEL = "claude-sonnet-4-6"             # pick your current model id

# 1. Create the WRITER agent once (store agent.id + agent.version).
agent = client.beta.agents.create(
    name="Deck Builder",
    model=MODEL,
    system="You build client-ready pitch decks as .pptx in the workspace.",
    tools=[{
        "type": "agent_toolset_20260401",
        "configs": [{"name": "read"}, {"name": "write"}],
    }],
    betas=BETAS,
)

# 2. New session per run — sessions take ONLY an agent pointer,
#    never model/system/tools (those live on the agent).
session = client.beta.sessions.create(agent=agent.id, betas=BETAS)

# 3. The rubric IS the gate. Every line must be independently gradeable.
RUBRIC = """\
# Pitch deck rubric — all criteria must pass
1. Exactly one headline claim per slide, stated as a sentence.
2. Every data point cites a named source on the same slide.
3. No slide has more than 40 words of body copy.
4. Title slide names the client and the single strategic idea.
5. Closing slide states one clear next action with an owner.
"""

# 4. define_outcome carries the task AND the rubric — no separate user.message.
client.beta.sessions.events.send(
    session.id,
    betas=BETAS,
    events=[{
        "type": "user.define_outcome",
        "description": "Build a 6-slide launch pitch deck for the client brief in /brief.md",
        "rubric": {"type": "text", "content": RUBRIC},
        "max_iterations": 5,          # optional; default 3, max 20
    }],
)

# 5. Stream events and read the terminal verdict.
TERMINAL = {"satisfied", "failed", "max_iterations_reached", "interrupted"}
with client.beta.sessions.events.stream(session.id, betas=BETAS) as stream:
    for ev in stream:
        if ev.type == "span.outcome_evaluation_start":
            print(f"grading iteration {ev.iteration} ...")
        elif ev.type == "span.outcome_evaluation_end":
            print(f"  -> {ev.result}\n{ev.explanation}")
            if ev.result in TERMINAL:
                shipped = ev.result == "satisfied"
                break
```

`shipped is True` only on `satisfied`. Everything else is a hold — that is the
go/no-go you gate downstream steps on.

## Recipe 2 — Turn the verdict into a pipeline decision

The `result` on `span.outcome_evaluation_end` is your enum:

| `result` | Meaning | What you do |
|---|---|---|
| `satisfied` | Every criterion met; session → idle | Ship it. Downstream may proceed. |
| `needs_revision` | Grader found gaps | Nothing — the agent auto-starts another iteration. |
| `max_iterations_reached` | Hit the cap unsatisfied | Escalate to a human; attach the last `explanation`. |
| `failed` | Rubric fundamentally mismatches the task | Fix the RUBRIC or the task, not the output. |
| `interrupted` | Cancelled mid-evaluation | Retry or treat as no-go. |

```python
def decide(result, explanation):
    if result == "satisfied":
        return ("ship", None)
    if result == "max_iterations_reached":
        return ("escalate", explanation)     # human review with the gap list
    if result == "failed":
        return ("fix_rubric", explanation)   # your rubric/task is wrong
    return ("hold", explanation)
```

Wire `("escalate", ...)` to a Slack/webhook so an agency reviewer sees exactly
which criteria the deck missed rather than an opaque "the agent gave up."

## Recipe 3 — Reusable rubric via the Files API

For a rubric you reuse across many sessions (e.g. a house deck standard), upload
it once and reference by id instead of inlining text:

```python
# Upload with the files beta, then:
events=[{
    "type": "user.define_outcome",
    "description": "...",
    "rubric": {"type": "file", "file_id": "file_abc123"},
    "max_iterations": 3,
}]
```

## Writing rubrics that actually gate

- **One check per line, binary.** "Slides are concise" is ungradeable; "no slide
  exceeds 40 words" is. The grader returns a per-criterion verdict — give it
  criteria it can pass/fail unambiguously.
- **Front-load the hard, cheap checks** so early iterations kill obvious misses.
- **A too-strict rubric = `max_iterations_reached` forever; a too-loose one =
  instant `satisfied` on junk.** Calibrate by running both a known-good and a
  known-bad artifact through it once.
- **`failed` is a signal about YOU, not the model** — it means the rubric can't
  be satisfied by any valid attempt at the task. Re-read your criteria.

## Verify

- `python3 -c "import anthropic, inspect; print(hasattr(anthropic.Anthropic().beta, 'sessions'))"`
  prints `True` on an SDK new enough for Managed Agents.
- Run Recipe 1 against a deliberately BAD brief and confirm you see
  `needs_revision` at least once before a terminal result — that proves the grader
  is looping, not rubber-stamping.
- Run it against a known-good artifact and confirm `satisfied` on iteration 0.
- Confirm the grader is independent: the `explanation` should reference your
  rubric criteria verbatim, not the writer's internal reasoning.
- Sanity-check the beta header is accepted (no 4xx about an unknown beta) — if
  rejected, your SDK or account lacks the current Managed Agents beta.

## Pitfalls

- **Stream deadlock.** If the SSE stream drops while an `agent.tool_use` is pending,
  the session can deadlock. Reconnect by fetching event history
  (`GET /v1/sessions/{id}/events`), de-duping by event id, then resuming the stream.
- **Don't put a `user.message` alongside `define_outcome`.** The `description`
  field IS the task; a redundant message can confuse what the writer works toward.
- **`max_iterations` is a budget, not a guarantee.** Reaching it does NOT mean
  success — always branch on `result`, never assume the last draft is shippable.
- **Grader ≠ your offline eval.** It grades the artifact in the workspace, not
  your test harness. If your rubric references files, make sure the agent's tools
  (`read`/`write`) can actually see them.
- **Beta churn.** The five `result` strings, the `span.outcome_evaluation_*` event
  names, and the `rubric`/`max_iterations` field shapes are all beta surface. Pin
  your SDK version and re-verify against the cookbook before a launch depends on
  an exact literal.
- **Cost blindness.** Each iteration runs the grader as a full agent. Cap
  `max_iterations` deliberately (default 3 is often enough) rather than defaulting
  to 20 and paying for a slow, expensive climb.
