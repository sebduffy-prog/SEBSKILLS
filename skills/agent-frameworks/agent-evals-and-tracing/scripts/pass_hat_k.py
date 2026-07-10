#!/usr/bin/env python3
"""Compute pass^k (tau-bench reliability metric) from per-task trial results.

pass^k = probability that a randomly chosen k-subset of a task's n trials is
ALL successful, averaged across tasks. Unbiased estimator per task with c
successes out of n trials: C(c, k) / C(n, k)  (0 when c < k).

This is NOT pass@k (at least one success). pass^k rewards consistency: one
flaky failure tanks the score. Use it when a single failure is costly
(customer-service policy adherence, financial actions).

Input: JSON list of {"task_id": str, "results": [bool, ...]} OR a CSV with
columns task_id,success (one row per trial). Reads stdin or a file arg.
"""
from __future__ import annotations
import sys, json, csv, io
from math import comb
from collections import defaultdict


def pass_hat_k_for_task(successes: int, trials: int, k: int) -> float:
    if k > trials:
        raise ValueError(f"k={k} exceeds n={trials} trials for a task")
    if successes < k:
        return 0.0
    return comb(successes, k) / comb(trials, k)


def load(text: str) -> dict[str, list[bool]]:
    text = text.strip()
    tasks: dict[str, list[bool]] = defaultdict(list)
    if text.startswith("[") or text.startswith("{"):
        data = json.loads(text)
        for row in data:
            tasks[str(row["task_id"])].extend(bool(x) for x in row["results"])
    else:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            val = str(row["success"]).strip().lower()
            tasks[str(row["task_id"])].append(val in ("1", "true", "yes", "pass"))
    return tasks


def main() -> int:
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    tasks = load(text)
    if not tasks:
        print("no tasks parsed", file=sys.stderr)
        return 1
    n_min = min(len(v) for v in tasks.values())
    print(f"tasks={len(tasks)}  min_trials={n_min}")
    for k in range(1, n_min + 1):
        scores = [pass_hat_k_for_task(sum(v), len(v), k) for v in tasks.values()]
        print(f"pass^{k} = {sum(scores) / len(scores):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
