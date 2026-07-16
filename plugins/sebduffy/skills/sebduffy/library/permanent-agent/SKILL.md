---
name: permanent-agent
category: building-agents
description: >
  Stand up an always-on, self-maintaining agent that outlives a single session.
  Use when someone wants a long-running / persistent / "24-7" / daemon / "agent that
  keeps working while I sleep" bot with durable tiered memory, a scheduled heartbeat
  wake-loop over an append-only task queue, a watchdog that self-health-checks and
  restarts on stall, hard per-run + daily token/$ budget caps, and a kill-switch file
  that halts everything. Ships a runnable orchestrator + config + a Voyager-style
  growing skill library so the agent survives restarts and cannot run away.
when_to_use:
  - User wants an agent that persists across sessions and restarts, not a one-shot chat
  - Recurring autonomous work on a schedule (poll inbox, monitor a feed, nightly maintenance)
  - A long-lived worker needs durable memory + a resumable task queue that survives crashes
  - You need runaway protection - budget caps + a kill-switch - on an autonomous loop
  - You want lifelong learning - the agent accumulates reusable skills/strategies over time
when_not_to_use:
  - One interactive session with no persistence needed - just run Claude Code directly
  - A single scheduled cron run with no memory/queue/watchdog - use the `schedule` skill or plain cron
  - Multi-agent fan-out for parallel independent tasks - use `dispatching-parallel-agents`
  - You only need managed cloud memory, not the full loop - use Letta / `letta` CLI directly
keywords:
  - permanent-agent
  - always-on
  - persistent-agent
  - heartbeat-loop
  - task-queue
  - durable-memory
  - watchdog
  - kill-switch
  - budget-cap
  - cron
  - systemd
  - skill-library
  - voyager
  - letta
  - self-healing
  - checkpoint
inputs_needed:
  - Agent goal + the periodic task it performs each wake
  - A durable state dir (SQLite/JSON) and wake cadence (cron/systemd/Railway schedule)
  - Budget policy - per-run + daily token/$ caps - and where the kill-switch file lives
produces:
  - orchestrator.py wake-loop (pull due tasks -> act -> checkpoint -> sleep)
  - Durable memory + append-only task queue + growing skill library on disk
  - Watchdog + schedule unit + config.yaml (cadence, budgets, caps, kill-switch path)
similar_to:
  - dispatching-parallel-agents
  - mcp-builder
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Permanent Agent

Build an agent that behaves like a **process, not a conversation**: it wakes on a
schedule, does a slice of work, checkpoints, and sleeps — indefinitely. Four pillars,
each borrowed from a proven system:

- **STATE** — durable tiered memory (Letta/MemGPT: core + archival + recall) plus an
  append-only task queue. Both survive process death.
- **LOOP** — a cron/systemd/Railway heartbeat wakes the orchestrator; it pulls *due*
  tasks, acts, checkpoints, sleeps.
- **HEALTH** — a watchdog checks liveness + last-progress timestamp and restarts on stall.
- **SAFETY** — per-run and daily token/$ budget caps + a kill-switch file that halts the
  loop instantly.

Lifelong learning (Voyager): a **skill library** of executable strategies grows over time
and is retrieved on later wakes, so the agent gets better instead of repeating itself.

## When to use

Reach for this when "run it once" is not enough — the agent must persist state, resume
after a crash, work on a cadence, and be impossible to leave running unbounded. If you
only need one scheduled invocation, use the `schedule` skill or a bare cron line instead.

## Prerequisites

- `python3` (3.9 on this Mac is fine — stdlib only: `sqlite3`, `json`, `os`, `time`).
- A wake mechanism: `cron`/`launchd` locally, `systemd` timer on Linux, or a Railway
  scheduled service in cloud. Pick one; the loop body is identical.
- An agent runtime you call from `act()` — the Claude Code CLI (`claude -p "..."`), the
  Anthropic SDK, or Letta (`pip install letta`; `letta server`) for managed memory.
- Decide your two hard numbers up front: `max_tokens_per_run` and `daily_token_budget`.

## Mechanism / Steps

### 1. Lay down durable state (append-only)

One directory is the whole agent. Append-only means a crash mid-write never corrupts
history — you replay to rebuild.

```
agent/
  config.yaml         # cadence, budgets, caps, kill-switch path
  memory.sqlite       # core (editable facts) + archival (vector/FTS) + recall (log)
  queue.jsonl         # append-only task queue, one JSON task per line
  skills.jsonl        # Voyager-style skill library: {name, when, code/prompt, uses}
  state.json          # checkpoint: last_run, cursor, in-flight task id
  heartbeat.txt       # last-progress epoch (watchdog reads this)
  spend.jsonl         # append-only ledger: {ts, run_id, tokens, usd}
  STOP                # kill-switch: presence halts the loop (absent = run)
```

Tiered memory mirrors Letta/MemGPT: **core** = small always-in-context facts you edit in
place; **archival** = large searchable store (SQLite FTS5 or a vector DB); **recall** =
the raw event log. Keep core tiny; page in from archival on demand.

### 2. The heartbeat loop (orchestrator)

Every wake runs the same guarded body. `scripts/orchestrator.py` is the reference:

```
load config -> if STOP exists: log + exit 0
             -> if daily budget spent: exit 0
             -> due = [t in queue.jsonl if t.due <= now and not t.done]
             -> for t in due (until per-run budget hit):
                    skill = retrieve_skill(t)          # Voyager: reuse a strategy
                    result, tokens = act(t, skill)     # call Claude / Letta / SDK
                    record_spend(tokens); write memory
                    if new strategy worked: append to skills.jsonl
                    mark t done (append tombstone line)
                    touch heartbeat.txt; checkpoint state.json
             -> exit 0   # scheduler re-invokes next tick; NO long-lived sleep
```

Critical design choices:

- **The scheduler is the sleep.** Exit cleanly each tick; let cron/systemd re-invoke. A
  crashed process is then just a missed tick, not a dead agent. (For a single always-up
  process instead, wrap the body in `while True: ...; time.sleep(interval)` — but you then
  own restart, so you need the watchdog in §4.)
- **Checkpoint after every task**, not at the end — so a crash resumes mid-batch.
- **Idempotent tasks.** Mark done by appending, and skip already-done ids on replay, so a
  re-run after a crash never double-acts.

### 3. Budget caps + kill-switch (SAFETY — do this before wiring `act`)

```python
# guardrails.py — refuse to act if any limit is blown
def preflight(cfg):
    if os.path.exists(cfg["kill_switch"]):        # STOP file present
        raise Halt("kill-switch engaged")
    spent = sum(x["tokens"] for x in today(cfg))  # from spend.jsonl
    if spent >= cfg["daily_token_budget"]:
        raise Halt(f"daily budget {cfg['daily_token_budget']} reached")

def charge(cfg, run_spent, delta):                # per-run cap, checked each task
    if run_spent + delta > cfg["max_tokens_per_run"]:
        raise Halt("per-run budget reached")
```

`touch agent/STOP` from anywhere halts the next tick within one cadence — the human
override. Log every halt with reason. Never let `act()` run before `preflight()` passes.

### 4. Watchdog (HEALTH)

A second, dumber timer (or the top of each wake) checks the heartbeat:

```
now - mtime(heartbeat.txt) > stall_threshold  ->  restart the agent unit
   (systemctl restart / launchctl kickstart / railway redeploy)
   and append an incident to recall memory
```

Keep the watchdog trivial and separate from the agent so a bug in `act()` can't disable
its own supervisor. `Restart=on-failure` in the systemd unit covers hard crashes; the
watchdog covers *silent stalls* (agent alive but not progressing).

### 5. Wake mechanism — pick one

- **launchd/cron (local Mac):** `*/15 * * * * cd /path/agent && python3 orchestrator.py`
- **systemd (Linux):** a `.service` with `Restart=on-failure` + a `.timer`
  (`OnUnitActiveSec=15min`). The timer is the heartbeat; `Restart` is the crash-watchdog.
- **Railway (cloud):** a service with a cron schedule (see `use-railway` skill) running
  `python3 orchestrator.py`; a Railway Volume holds `agent/` so state persists across deploys.

### 6. Lifelong learning (Voyager skill library)

On success with a novel approach, append a skill: `{name, when_to_use, code_or_prompt,
uses:0}`. On each task, `retrieve_skill()` matches by keyword/embedding and feeds the top
strategy into `act()`. Increment `uses`; periodically prune never-used skills. Over weeks
the agent stops re-deriving solved problems — the core Voyager result.

### 7. Wire it up

Fill `act()` to call your runtime (e.g. `subprocess claude -p`, Anthropic SDK, or a Letta
agent id), point `config.yaml` at your paths/limits, install the schedule unit, and seed
`queue.jsonl` with one task. Watch `heartbeat.txt` advance.

## Verify

```bash
python3 scripts/orchestrator.py            # one tick, dry-run: prints plan, no LLM call
touch agent/STOP && python3 scripts/orchestrator.py   # must exit "kill-switch engaged"
rm agent/STOP
# force budget: set daily_token_budget: 0 -> tick must halt "daily budget reached"
# crash test: kill mid-run, re-run -> resumes, no task acted twice (check spend.jsonl)
stat -f %m agent/heartbeat.txt             # advances after a real tick
```

Green when: STOP halts within one tick, a zero budget halts, a mid-run kill resumes
without double-charging, and the heartbeat mtime climbs on progress.

## Pitfalls

- **Long in-process `sleep()`.** A process that sleeps for hours is a process that dies
  unnoticed. Prefer exit-and-be-rescheduled; if you must stay up, the watchdog is mandatory.
- **Non-idempotent tasks.** Without dedupe on task id, a crash-resume double-sends emails
  or double-spends. Append tombstones and skip done ids on replay.
- **Budget checked only per-run.** A tight per-run cap with a loose/absent daily cap still
  bleeds money across many wakes. Enforce both, from the append-only ledger.
- **Watchdog inside the agent process.** If it shares the crashing process it can't restart
  anything. Keep it external (systemd `Restart`, separate timer, or Railway healthcheck).
- **Unbounded memory growth.** Append-only files grow forever — compact `recall`/`spend`
  into monthly archives and prune stale skills, or startup slows and context blows up.
- **Kill-switch that needs the agent to honor it in-loop only.** Also give the human a hard
  stop (disable the timer / scale service to 0) for when the loop itself is wedged.
- **Secrets in the state dir.** `agent/` is durable and often on a shared volume — keep API
  keys in env/secret manager, never checkpointed into `state.json` or memory.
