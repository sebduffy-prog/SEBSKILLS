#!/usr/bin/env python3
"""dream_loop.py — one idle-time self-improvement cycle, gated by a frozen eval.

REPLAY recent transcripts -> DISTIL lessons -> PROPOSE edits (to a shadow copy)
-> run the FROZEN eval on baseline + candidate -> ACCEPT only if candidate wins
by >= margin -> append to CHANGELOG. Nothing is accepted without a measured win,
and the frozen set is never written to by this loop (anti-overfit guardrail).

The LLM steps (distil, propose, run-a-task, grade) shell out to the `claude`
CLI in headless mode (`claude -p`). Swap `_claude()` for any provider.

Deterministic parts (bucketing, gating, changelog, atomic promote) are unit-safe
and exercised by `--dry-run`, which stubs every LLM call.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ACCEPT_MARGIN = 0.0   # candidate must beat baseline by strictly more than this
REPLAY_N = 20         # transcripts to replay per cycle


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _claude(prompt: str, dry: bool, stub: str = "") -> str:
    """One headless model call. In --dry-run return the stub instead."""
    if dry:
        return stub
    out = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=600,
    )
    if out.returncode != 0:
        raise RuntimeError(f"claude failed: {out.stderr.strip()[:400]}")
    return out.stdout.strip()


# ---- REPLAY -----------------------------------------------------------------
def replay(root: Path, n: int) -> tuple[list, list]:
    """Read last n transcripts, bucket into (success, fail) by their verdict."""
    tdir = root / "transcripts"
    files = sorted(tdir.glob("*.json"), key=lambda p: p.stat().st_mtime)[-n:]
    success, fail = [], []
    for f in files:
        try:
            t = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue  # never trust file content — skip malformed traces
        (success if t.get("passed") else fail).append(t)
    return success, fail


# ---- DISTIL + PROPOSE -------------------------------------------------------
def distil(success: list, fail: list, dry: bool) -> list[dict]:
    """Turn traces into reusable strategy items (ReasoningBank-style)."""
    prompt = (
        "You are the dreaming agent. From these SUCCESS and FAIL traces, extract "
        "reusable strategies. Return a JSON array of objects "
        '{"title","when","do","evidence"}. Learn from failures too.\n\n'
        f"SUCCESS ({len(success)}):\n{json.dumps(success)[:6000]}\n\n"
        f"FAIL ({len(fail)}):\n{json.dumps(fail)[:6000]}"
    )
    stub = json.dumps([{"title": "stub-strategy", "when": "dry-run",
                        "do": "noop", "evidence": "dry-run"}])
    raw = _claude(prompt, dry, stub)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def propose(root: Path, strategies: list, shadow: Path, dry: bool) -> str:
    """Copy mutable target to a shadow dir and ask the model to edit it in place.
    Returns a human-readable summary of the proposed diff."""
    target = root / "target"               # the mutable skill/prompt files
    if shadow.exists():
        shutil.rmtree(shadow)
    shutil.copytree(target, shadow)
    prompt = (
        "Given these distilled strategies, edit the prompt/skill files under "
        f"{shadow} to encode them. Make the smallest change that could raise the "
        "frozen-eval score. Then print a one-paragraph summary of what you "
        f"changed.\n\nSTRATEGIES:\n{json.dumps(strategies)[:6000]}"
    )
    return _claude(prompt, dry, stub="dry-run: no edit applied")


# ---- FROZEN EVAL ------------------------------------------------------------
def run_eval(root: Path, target_dir: Path, dry: bool, dry_score: float) -> float:
    """Score target_dir against the frozen held-out set. Never writes the set."""
    if dry:
        return dry_score
    tasks = [json.loads(l) for l in
             (root / "evals" / "frozen_set.jsonl").read_text().splitlines() if l.strip()]
    if not tasks:
        raise RuntimeError("frozen_set.jsonl is empty — refusing to gate on nothing")
    passed = 0
    for t in tasks:
        ans = _claude(f"[using files in {target_dir}]\n{t['prompt']}", dry=False)
        grade = _claude(
            f"TASK: {t['prompt']}\nRUBRIC: {t['rubric']}\nANSWER: {ans}\n"
            'Reply exactly PASS or FAIL.', dry=False)
        passed += 1 if grade.strip().upper().startswith("PASS") else 0
    return passed / len(tasks)


# ---- GATE + AUDIT -----------------------------------------------------------
def gate(root: Path, baseline: float, candidate: float, margin: float,
         strategies: list, summary: str, shadow: Path) -> bool:
    accepted = candidate > baseline + margin
    if accepted:
        # append-only memory: only distilled wins enter the bank
        bank = root / "memory" / "reasoning_bank.jsonl"
        with bank.open("a") as fh:
            for s in strategies:
                fh.write(json.dumps({**s, "ts": _now(), "score": candidate}) + "\n")
        # atomic promote of the shadow edits into the live target
        target = root / "target"
        tmp = target.with_suffix(".new")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(shadow, tmp)
        shutil.rmtree(target)
        os.replace(tmp, target)
    verdict = "ACCEPT" if accepted else "REJECT"
    log = root / "dreams" / "CHANGELOG.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as fh:
        fh.write(f"\n## {_now()} — {verdict}\n"
                 f"- baseline={baseline:.3f} candidate={candidate:.3f} "
                 f"margin={margin} delta={candidate - baseline:+.3f}\n"
                 f"- strategies: {len(strategies)}\n"
                 f"- change: {summary[:400]}\n")
    return accepted


def cycle(root: Path, dry: bool, margin: float, n: int,
          dry_base: float = 0.5, dry_cand: float = 0.6) -> bool:
    success, fail = replay(root, n)
    strategies = distil(success, fail, dry)
    with tempfile.TemporaryDirectory() as td:
        shadow = Path(td) / "shadow"
        summary = propose(root, strategies, shadow, dry)
        baseline = run_eval(root, root / "target", dry, dry_base)
        candidate = run_eval(root, shadow, dry, dry_cand)
        return gate(root, baseline, candidate, margin, strategies, summary, shadow)


def scaffold(root: Path) -> None:
    for p in ["memory", "evals", "dreams", "transcripts", "target"]:
        (root / p).mkdir(parents=True, exist_ok=True)
    (root / "memory" / "reasoning_bank.jsonl").touch()
    fs = root / "evals" / "frozen_set.jsonl"
    if not fs.exists():
        fs.write_text(json.dumps({"prompt": "2+2?", "rubric": "answer is 4"}) + "\n")
    (root / "target" / "SYSTEM_PROMPT.md").touch()
    print(f"scaffolded {root}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--margin", type=float, default=ACCEPT_MARGIN)
    ap.add_argument("--replay-n", type=int, default=REPLAY_N)
    a = ap.parse_args()
    if a.init:
        scaffold(a.root)
        return 0
    accepted = cycle(a.root, a.dry_run, a.margin, a.replay_n)
    print("ACCEPTED" if accepted else "REJECTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
