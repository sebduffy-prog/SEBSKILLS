#!/usr/bin/env python3
"""Permanent-agent heartbeat orchestrator (stdlib-only, py3.9+).

One tick = pull due tasks -> guardrail preflight -> act -> record spend ->
checkpoint -> touch heartbeat -> exit. The scheduler (cron/systemd/Railway)
re-invokes; the process never sleeps for long. Safe to crash: state is
append-only and tasks are idempotent (done ids are skipped on replay).

Dry-run by default (no LLM call): prints the plan. Set act() to your runtime.
Layout lives under AGENT_DIR (default ./agent).
"""
import json
import os
import sys
import time

AGENT_DIR = os.environ.get("AGENT_DIR", os.path.join(os.getcwd(), "agent"))


class Halt(Exception):
    """Raised to stop the tick cleanly (kill-switch or budget)."""


def _p(name):
    return os.path.join(AGENT_DIR, name)


def load_config():
    """Read config.yaml with a tiny hand-rolled parser (no PyYAML dep)."""
    cfg = {
        "kill_switch": _p("STOP"),
        "max_tokens_per_run": 50_000,
        "daily_token_budget": 200_000,
        "stall_threshold_sec": 3600,
    }
    path = _p("config.yaml")
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                key, val = (s.strip() for s in line.split(":", 1))
                if val.replace("_", "").isdigit():
                    cfg[key] = int(val.replace("_", ""))
                elif val:
                    cfg[key] = val
    return cfg


def _read_jsonl(name):
    path = _p(name)
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _append_jsonl(name, obj):
    with open(_p(name), "a") as fh:
        fh.write(json.dumps(obj) + "\n")


def done_ids():
    """Task ids already completed (tombstones), for idempotent replay."""
    return {t["id"] for t in _read_jsonl("queue.jsonl") if t.get("done")}


def due_tasks(now):
    seen_done = done_ids()
    tasks, live = _read_jsonl("queue.jsonl"), {}
    for t in tasks:
        if t.get("done") or t["id"] in seen_done:
            continue
        if t.get("due", 0) <= now:
            live[t["id"]] = t  # last live definition wins
    return list(live.values())


def today_spend(cfg):
    day = time.strftime("%Y-%m-%d")
    return sum(x["tokens"] for x in _read_jsonl("spend.jsonl")
               if x.get("day") == day)


def preflight(cfg):
    if os.path.exists(cfg["kill_switch"]):
        raise Halt("kill-switch engaged")
    if today_spend(cfg) >= cfg["daily_token_budget"]:
        raise Halt(f"daily budget {cfg['daily_token_budget']} reached")


def charge(cfg, run_spent, delta):
    if run_spent + delta > cfg["max_tokens_per_run"]:
        raise Halt("per-run budget reached")


def retrieve_skill(task):
    """Voyager: return best-matching stored strategy (keyword match here;
    swap for embedding similarity in production)."""
    words = set(str(task.get("goal", "")).lower().split())
    best, best_score = None, 0
    for s in _read_jsonl("skills.jsonl"):
        score = len(words & set(str(s.get("when", "")).lower().split()))
        if score > best_score:
            best, best_score = s, score
    return best


def act(task, skill, dry_run):
    """REPLACE ME with your runtime call. Return (result, tokens_used).

    Real examples:
      subprocess.run(["claude","-p", prompt], ...)   # Claude Code CLI
      client.messages.create(...)                    # Anthropic SDK
      letta_client.send_message(agent_id, prompt)    # Letta managed memory
    """
    if dry_run:
        hint = skill["name"] if skill else "none"
        print(f"  [dry-run] would act on {task['id']} (skill={hint})")
        return ("dry-run", 0)
    raise NotImplementedError("wire act() to your agent runtime")


def checkpoint(state):
    tmp = _p("state.json.tmp")
    with open(tmp, "w") as fh:
        json.dump(state, fh)
    os.replace(tmp, _p("state.json"))  # atomic


def touch_heartbeat():
    with open(_p("heartbeat.txt"), "w") as fh:
        fh.write(str(int(time.time())))


def tick(dry_run=True):
    os.makedirs(AGENT_DIR, exist_ok=True)
    cfg = load_config()
    run_id = int(time.time())
    day = time.strftime("%Y-%m-%d")
    try:
        preflight(cfg)
    except Halt as h:
        print(f"HALT: {h}")
        return 0

    run_spent = 0
    for task in due_tasks(run_id):
        try:
            charge(cfg, run_spent, task.get("est_tokens", 1000))
        except Halt as h:
            print(f"HALT: {h}")
            break
        skill = retrieve_skill(task)
        result, tokens = act(task, skill, dry_run)
        run_spent += tokens
        _append_jsonl("spend.jsonl",
                      {"ts": run_id, "day": day, "run_id": run_id,
                       "tokens": tokens, "task": task["id"]})
        _append_jsonl("queue.jsonl",
                      {"id": task["id"], "done": True, "result": str(result)[:200]})
        checkpoint({"last_run": run_id, "last_task": task["id"]})
        touch_heartbeat()
    else:
        touch_heartbeat()  # progressed (or nothing due) => alive
    return 0


if __name__ == "__main__":
    sys.exit(tick(dry_run="--live" not in sys.argv))
