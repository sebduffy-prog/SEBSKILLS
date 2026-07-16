---
name: human-in-the-loop-approval
category: agent-frameworks
description: >
  Put a durable human approval gate in front of any consequential agent action — send email,
  post to Slack, spend money, deploy, delete, DM a client. Pause the run, surface the exact
  action for a person to approve / reject / edit, and resume where it stopped even after a crash
  or a day's wait. Grounds the LangGraph interrupt() + Command(resume=) pattern plus a
  framework-agnostic SQLite gate for plain scripts. Use when asked to add an approval
  step, a "confirm before doing X" gate, human oversight, a review checkpoint, or a durable
  pause-and-resume before an irreversible tool call.
when_to_use:
  - "Gate an irreversible or external action (send email, post, pay, deploy, delete) behind a human yes/no"
  - "Let a reviewer edit the agent's proposed output/args before it executes, not just approve it"
  - "Pause a run for approval and resume it later — possibly in a different process after a crash"
  - "Review or rewrite a tool call's arguments before the tool actually fires"
  - "Add oversight to a plain (non-LangGraph) Python agent/script with no orchestration framework"
  - "Collect and validate a human's input mid-run (age, budget, missing field) before continuing"
when_not_to_use:
  - "Building the whole LangGraph graph/supervisor/fan-out topology → use langgraph-durable-workflows"
  - "Deciding whether YOU (the agent) should ask vs act on a task → use autonomy-policy"
  - "Approving a visual/UI change before shipping it → use design-approval-gate"
  - "Blocking prompt-injection / jailbreak attempts rather than gating an action → use llm-guardrails-injection-defense"
  - "OpenAI Agents SDK handoff/tool-approval specifics → use openai-agents-sdk"
keywords: [human-in-the-loop, hitl, approval gate, interrupt, command resume, langgraph, checkpointer, durable execution, pause and resume, tool approval, review checkpoint, oversight, thread_id, breakpoint, confirm before action, resumable]
similar_to: [langgraph-durable-workflows, autonomy-policy, design-approval-gate, openai-agents-sdk, llm-guardrails-injection-defense]
inputs_needed:
  - "The consequential action to gate and what a reviewer needs to see to decide (the payload)"
  - "The four modes you need: approve/reject, edit-then-run, review tool args, or collect input"
  - "Persistence target: InMemorySaver (dev, same process) or SqliteSaver/Postgres (survives restart)"
  - "A unique thread_id per task/session, and the channel a human uses to respond (CLI, UI, Slack)"
produces: A runnable durable approval gate — LangGraph interrupt()/Command(resume=) node or a stdlib SQLite gate (scripts/gate.py) — that pauses before the action and resumes on the human's decision.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Human-in-the-Loop Approval Gate

A **gate** pauses an agent right before a consequential action, hands a human the exact
thing about to happen, and resumes only on their decision. **Durable** means the pause is
persisted: the human can take a minute or a day, and a crashed/restarted process resumes
from the same point — not from the top.

## When to use

The moment an agent is about to do something external or irreversible — send an email, post
to Slack, charge a card, run a deploy, delete a row, message a client — and a person should
sign off first. If you only need to decide whether *you* should ask the user vs. proceed,
that's `autonomy-policy`. If you're building the whole graph, that's
`langgraph-durable-workflows` — this skill is just the gate that goes inside it.

## Prerequisites

Two paths. Use LangGraph if you're already in it; use the stdlib gate for plain scripts.

```bash
# Path A — LangGraph (durable interrupts)
pip install langgraph
pip install langgraph-checkpoint-sqlite   # SqliteSaver: survives process restart

# Path B — framework-agnostic gate (this skill's helper): no deps, Python 3.9+ stdlib
```

## Recipe A — LangGraph interrupt() gate (the real durable pattern)

`interrupt()` pauses inside a node and surfaces a payload to the caller; `Command(resume=v)`
feeds the human's decision back in as the return value of `interrupt()`. **A checkpointer is
mandatory** — no checkpointer, no pause. Use `SqliteSaver` (not `InMemorySaver`) if the pause
must survive a restart.

```python
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver   # durable across restarts

class State(TypedDict):
    draft: str
    sent: bool

def send_email_node(state: State) -> Command[Literal["deliver", "__end__"]]:
    # interrupt() PAUSES here; the payload is what the reviewer sees.
    decision = interrupt({
        "action": "send_email",
        "to": "cfo@client.com",
        "body": state["draft"],
        "options": ["approve", "edit", "reject"],
    })
    if decision == "reject":
        return Command(goto=END)
    if isinstance(decision, dict) and decision.get("edit"):
        return Command(update={"draft": decision["edit"]}, goto="deliver")
    return Command(goto="deliver")

def deliver(state: State):
    # real send happens ONLY past the gate
    return {"sent": True}

b = StateGraph(State)
b.add_node("send_email", send_email_node)
b.add_node("deliver", deliver)
b.add_edge(START, "send_email")
b.add_edge("deliver", END)

with SqliteSaver.from_conn_string("checkpoints.db") as saver:
    graph = b.compile(checkpointer=saver)
    cfg = {"configurable": {"thread_id": "email-42"}}   # unique per task

    result = graph.invoke({"draft": "Hi, Q3 numbers attached.", "sent": False}, cfg)
    if "__interrupt__" in result:                        # paused, awaiting human
        payload = result["__interrupt__"][0].value
        print("NEEDS APPROVAL:", payload)
        # ...process can EXIT here; state is on disk under thread_id "email-42"...

# Later — even a brand-new process — reopen the same db + thread_id and resume:
with SqliteSaver.from_conn_string("checkpoints.db") as saver:
    graph = b.compile(checkpointer=saver)
    final = graph.invoke(Command(resume="approve"), {"configurable": {"thread_id": "email-42"}})
    print("sent:", final["sent"])   # True
```

### The four patterns (all just shapes of the payload + resume value)

- **Approve / reject** — resume with `True`/`False`; branch with `Command(goto=...)`.
- **Edit then run** — surface the draft, resume with the edited text, `Command(update=...)`.
- **Review tool args** — call `interrupt()` *inside the `@tool`* with the pending args; resume
  with approved (or corrected) args before the tool executes.
- **Collect + validate input** — `interrupt()` the question; if the resumed answer is invalid,
  route back via a **conditional edge** (never a `while` loop) and interrupt again.

## Recipe B — framework-agnostic durable gate (`scripts/gate.py`)

For plain scripts/agents with no orchestrator. State is a SQLite file, so a pending request
survives a crash and can be approved out-of-band (CLI, cron, a teammate) and enforced later.

```bash
G=scripts/gate.py
# 1) Agent submits the action for review (returns an id), then STOPS.
ID=$(python3 $G --db approvals.db submit send_email --payload '{"to":"cfo@x.com","subj":"Q3"}')

# 2) Guard immediately before the real action — exit 10=pending, 20=rejected, 0=approved.
python3 $G --db approvals.db enforce "$ID" || { echo "blocked"; exit 0; }

# 3) A human approves out-of-band, any time, any process:
python3 $G --db approvals.db approve "$ID" --by seb --note "numbers checked"

# 4) Re-run the guard; now it passes and the agent proceeds to send.
python3 $G --db approvals.db enforce "$ID" && echo "APPROVED — sending"
```

In-process, wrap the consequential call:

```python
from gate import Gate, PendingApproval, Rejected
g = Gate("approvals.db")
rid = g.submit("deploy_prod", {"sha": "9ada0c3", "env": "prod"})
try:
    g.enforce(rid)          # raises until a human approves
    deploy()                # only past the gate
except (PendingApproval, Rejected) as e:
    notify_human(str(e))    # park it; resume later with the same rid
```

## Verify

```bash
python3 -c "import ast; ast.parse(open('scripts/gate.py').read()); print('gate.py parses')"
# End-to-end across simulated process restarts (submit → block → approve → pass → reject):
python3 scripts/gate.py --db /tmp/hitl.db submit x && \
python3 scripts/gate.py --db /tmp/hitl.db list --status pending
```

For Recipe A: after the first `invoke`, confirm `"__interrupt__"` is in the result and that a
**second, separate** `invoke(Command(resume=...))` on the same `thread_id` returns `sent: True`
— proving the resume actually re-entered the paused node.

## Pitfalls

- **No checkpointer = no pause.** `interrupt()` without a compiled checkpointer raises. And
  `InMemorySaver` does NOT survive a restart — use `SqliteSaver`/`PostgresSaver` for real durability.
- **The whole node re-runs on resume.** Everything *before* `interrupt()` executes again. Put
  side effects (DB writes, the actual send) *after* the gate, and keep pre-gate work idempotent.
- **Never wrap `interrupt()` in try/except** — it works by raising a control-flow exception; a
  bare `except` swallows it and the pause silently never happens.
- **Reused thread_id = crossed wires.** One unique `thread_id` per task/user; reusing one
  resumes the wrong run. The SQLite gate uses a fresh id per `submit` for the same reason.
- **Gate the action, not the plan.** Put the interrupt on the last hop before the irreversible
  call, so an approval can't go stale between "approved" and "executed".
- **Keep interrupt order deterministic.** Don't conditionally skip an `interrupt()` mid-node;
  branch with conditional edges (Recipe A) instead, or resume values map to the wrong prompts.
- **Payloads must be JSON-serializable** — surface plain dicts/strings a reviewer can read, not
  live objects or functions.
