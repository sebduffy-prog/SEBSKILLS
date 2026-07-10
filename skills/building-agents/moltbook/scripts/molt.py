#!/usr/bin/env python3
"""molt.py — externally-gated multi-agent improvement loop ("moltbook").

One molt round: N proposers cross-revise (MoA-style) -> critique vs a versioned
rubric -> AUDIT (child must beat parent by >= delta on a REAL external eval) ->
VERIFICATION (independent judge panel; any veto rejects) -> keep-all archive.
Stop on epsilon-plateau + K-patience, or budget cap.

The four model-facing steps are dependency-injected (propose_fn, critique_fn,
verify_fn, eval_fn) so the control logic below is pure and unit-testable, and the
same orchestrator drives either mocks (tests) or the real Claude API (see
claude_adapters() at the bottom). eval_fn is HARD-REQUIRED: with no external eval
the loop collapses to plain self-critique and MUST refuse to promote — pass
eval_fn=None to see that guard fire.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional, Sequence

# ---- types --------------------------------------------------------------
# propose_fn(parent_text, siblings, rubric, persona) -> str
ProposeFn = Callable[[str, Sequence[str], str, str], str]
# critique_fn(text, rubric) -> str
CritiqueFn = Callable[[str, str], str]
# verify_fn(parent, child, rubric, judge_id) -> bool   (True = approve)
VerifyFn = Callable[[str, str, str, str], bool]
# eval_fn(text) -> float   (higher is better; the ONLY source of truth for AUDIT)
EvalFn = Callable[[str], float]


@dataclass
class Config:
    proposers: Sequence[str] = ("skeptic", "maximalist", "minimalist")
    verifiers: Sequence[str] = ("judge-a", "judge-b", "judge-c")
    max_rounds: int = 12
    delta: float = 0.01          # AUDIT margin: child must beat parent by >= delta
    epsilon: float = 0.005       # plateau threshold on best-score improvement
    patience: int = 3            # K consecutive sub-epsilon rounds -> converged
    max_calls: int = 400         # hard budget across ALL model calls
    require_unanimous: bool = True  # any veto rejects (majority if False)


@dataclass
class MoltRecord:
    round: int
    parent_id: int
    persona: str
    text: str
    parent_score: float
    child_score: float
    audit_pass: bool
    verify_votes: list
    accepted: bool
    ts: float = field(default_factory=time.time)


# ---- pure gates ---------------------------------------------------------

def audit_gate(parent_score: float, child_score: float, delta: float) -> bool:
    """AUDIT: promote ONLY if the external eval improves by at least delta."""
    return (child_score - parent_score) >= delta


def verification_gate(votes: Sequence[bool], require_unanimous: bool) -> bool:
    """VERIFICATION: any veto rejects (unanimous), else strict majority."""
    if not votes:
        return False
    if require_unanimous:
        return all(votes)
    return sum(1 for v in votes if v) > len(votes) / 2


def converged(best_history: Sequence[float], epsilon: float, patience: int) -> bool:
    """Converged if the last `patience` best-score gains are each < epsilon."""
    if len(best_history) <= patience:
        return False
    recent = best_history[-(patience + 1):]
    gains = [recent[i + 1] - recent[i] for i in range(len(recent) - 1)]
    return all(g < epsilon for g in gains)


# ---- archive ------------------------------------------------------------

def append_archive(path: str, rec: MoltRecord) -> None:
    """Keep-ALL archive: every proposal (accepted or not) is one JSONL line."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec)) + "\n")


# ---- orchestrator -------------------------------------------------------

def run_molt(
    seed_text: str,
    rubric: str,
    propose_fn: ProposeFn,
    critique_fn: CritiqueFn,
    verify_fn: VerifyFn,
    eval_fn: Optional[EvalFn],
    cfg: Config = Config(),
    archive_path: str = "archive.jsonl",
) -> dict:
    if eval_fn is None:
        raise ValueError(
            "eval_fn is HARD-REQUIRED. With no external eval, AUDIT cannot verify "
            "that a molt beats its parent — the loop would collapse to self-critique. "
            "Provide a real eval (unit tests / metric / benchmark) or do not run."
        )

    calls = 0
    best_text = seed_text
    best_score = eval_fn(seed_text); calls += 1
    best_history = [best_score]
    parent_id = 0
    next_id = 1
    accepted_count = 0

    for rnd in range(1, cfg.max_rounds + 1):
        if calls >= cfg.max_calls:
            break
        siblings: list = []          # MoA cross-revision: proposers see prior peers
        round_best_child = best_score
        round_best_text = best_text

        for persona in cfg.proposers:
            if calls >= cfg.max_calls:
                break
            child = propose_fn(best_text, siblings, rubric, persona); calls += 1
            siblings.append(child)
            _ = critique_fn(child, rubric); calls += 1  # rubric-anchored self-critique

            child_score = eval_fn(child); calls += 1
            a_pass = audit_gate(best_score, child_score, cfg.delta)

            votes: list = []
            if a_pass:                # only spend judges on audit survivors
                for judge in cfg.verifiers:
                    if calls >= cfg.max_calls:
                        break
                    votes.append(bool(verify_fn(best_text, child, rubric, judge)))
                    calls += 1
            v_pass = a_pass and verification_gate(votes, cfg.require_unanimous)

            rec = MoltRecord(rnd, parent_id, persona, child, best_score,
                             child_score, a_pass, votes, v_pass)
            append_archive(archive_path, rec)

            if v_pass and child_score > round_best_child:
                round_best_child, round_best_text = child_score, child

        if round_best_child > best_score:
            best_score, best_text = round_best_child, round_best_text
            parent_id = next_id; next_id += 1
            accepted_count += 1
        best_history.append(best_score)

        if converged(best_history, cfg.epsilon, cfg.patience):
            break

    return {
        "best_text": best_text,
        "best_score": best_score,
        "rounds": len(best_history) - 1,
        "molts_accepted": accepted_count,
        "calls_used": calls,
        "score_history": best_history,
    }


# ---- Claude adapters (real run) ----------------------------------------

def claude_adapters(model_map: dict, api_key: Optional[str] = None):
    """Return (propose_fn, critique_fn, verify_fn) bound to the Anthropic SDK.

    model_map maps persona/judge id -> Claude model id, e.g.
    {"skeptic": "claude-opus-4-6", "minimalist": "claude-3-5-haiku-latest", ...}.
    Heterogeneity (different models AND different persona prompts) is what makes
    the panel's votes independent — do not point every id at one model.
    """
    from anthropic import Anthropic  # guarded import; only needed for real runs
    client = Anthropic(api_key=api_key)

    def _msg(model: str, system: str, user: str) -> str:
        r = client.messages.create(
            model=model, max_tokens=2000,
            system=system, messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in r.content if b.type == "text")

    def propose_fn(parent, siblings, rubric, persona):
        peers = "\n\n".join(f"[peer] {s}" for s in siblings) or "(none yet)"
        sys = (f"You are the '{persona}' reviser. Improve the CANDIDATE to score "
               f"higher against the RUBRIC. Return ONLY the revised artifact.")
        usr = f"RUBRIC:\n{rubric}\n\nCANDIDATE:\n{parent}\n\nPEER DRAFTS:\n{peers}"
        return _msg(model_map.get(persona, next(iter(model_map.values()))), sys, usr)

    def critique_fn(text, rubric):
        sys = "List concrete, rubric-anchored weaknesses. Be terse."
        return _msg(next(iter(model_map.values())), sys,
                    f"RUBRIC:\n{rubric}\n\nARTIFACT:\n{text}")

    def verify_fn(parent, child, rubric, judge):
        sys = (f"You are independent verifier '{judge}'. Does CHILD strictly beat "
               f"PARENT on the RUBRIC with no regressions? Answer YES or NO only.")
        out = _msg(model_map.get(judge, next(iter(model_map.values()))), sys,
                   f"RUBRIC:\n{rubric}\n\nPARENT:\n{parent}\n\nCHILD:\n{child}")
        return out.strip().upper().startswith("YES")

    return propose_fn, critique_fn, verify_fn


# ---- self-test (no network) --------------------------------------------

if __name__ == "__main__":
    import random
    random.seed(7)
    TARGET = "the quick brown fox"

    def toy_eval(text):  # external "benchmark": char-overlap ratio to target
        hits = sum(1 for a, b in zip(text, TARGET) if a == b)
        return hits / max(len(TARGET), 1)

    def toy_propose(parent, siblings, rubric, persona):
        chars = list(parent.ljust(len(TARGET))[:len(TARGET)])
        i = random.randrange(len(chars))
        chars[i] = TARGET[i] if random.random() < 0.6 else random.choice("abcde ")
        return "".join(chars)

    def toy_critique(text, rubric):
        return "ok"

    def toy_verify(parent, child, rubric, judge):
        return toy_eval(child) > toy_eval(parent)  # honest independent judge

    out = run_molt("xxxxxxxxxxxxxxxxxxx", "match the target string",
                   toy_propose, toy_critique, toy_verify, toy_eval,
                   Config(max_rounds=40, delta=0.001, epsilon=0.001, patience=4,
                          max_calls=2000),
                   archive_path="/tmp/molt_selftest.jsonl")

    assert out["best_score"] >= 0.0
    assert out["molts_accepted"] >= 1, "expected at least one verified molt"
    assert audit_gate(0.5, 0.52, 0.01) and not audit_gate(0.5, 0.505, 0.01)
    assert verification_gate([True, True, True], True)
    assert not verification_gate([True, True, False], True)
    assert verification_gate([True, True, False], False)
    assert converged([0.9, 0.901, 0.902, 0.9025, 0.903], 0.005, 3)
    assert not converged([0.1, 0.3, 0.5, 0.7], 0.005, 3)
    try:
        run_molt("x", "r", toy_propose, toy_critique, toy_verify, None)
        raise SystemExit("FAIL: missing-eval guard did not fire")
    except ValueError:
        pass
    print("OK", {k: out[k] for k in ("best_score", "molts_accepted",
                                     "rounds", "calls_used")})
