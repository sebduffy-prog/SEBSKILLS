#!/usr/bin/env python3
"""Best-model-per-step pipeline: each step runs on the model best suited to it,
with a typed, schema-validated handoff of state between steps.

One vendor-agnostic call path (litellm), a per-step model map, and Pydantic
models as the contract between steps. Swap the STEP_MODELS map to re-route a
step to a different model/vendor without touching step logic.

    export ANTHROPIC_API_KEY=...   # + OPENAI_API_KEY / GEMINI_API_KEY as used
    python3 pipeline.py "Build a function that dedupes a CSV by email column"

Override any step's model from the env, e.g.:
    STEP_MODEL_code=openai/gpt-5.1  python3 pipeline.py "..."
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Type, TypeVar

from pydantic import BaseModel, ValidationError

try:
    import litellm
except ImportError:
    sys.exit("pip install 'litellm>=1.0' pydantic")

# ---- Per-step model routing --------------------------------------------------
# Right model for the job, not one model for everything. Confirm current IDs in
# each vendor's docs; these go stale. Any litellm-supported string works.
STEP_MODELS: dict[str, str] = {
    "plan":      os.getenv("STEP_MODEL_plan",      "anthropic/claude-opus-4-6"),     # deep reasoning
    "code":      os.getenv("STEP_MODEL_code",      "openai/gpt-5.1"),                 # coding
    "review":    os.getenv("STEP_MODEL_review",    "anthropic/claude-sonnet-4-6"),    # critique
    "summarize": os.getenv("STEP_MODEL_summarize", "anthropic/claude-haiku-4-5"),     # cheap bulk
}

# ---- Typed handoff contracts (the state passed BETWEEN steps) -----------------
class Plan(BaseModel):
    approach: str
    steps: list[str]

class Code(BaseModel):
    language: str
    source: str

class Review(BaseModel):
    passed: bool
    issues: list[str]

class Summary(BaseModel):
    tldr: str

T = TypeVar("T", bound=BaseModel)


def run_step(step: str, schema: Type[T], system: str, user: str, retries: int = 2) -> T:
    """Call the step's assigned model and parse+validate into `schema`.

    JSON is requested in-prompt AND via response_format for providers that honour
    it; the Pydantic parse is the real gate. On a validation miss we re-ask with
    the error so the model self-corrects — never return unvalidated state."""
    model = STEP_MODELS[step]
    instruction = f"{system}\nReturn ONLY JSON matching this schema:\n{json.dumps(schema.model_json_schema())}"
    messages = [{"role": "system", "content": instruction},
                {"role": "user", "content": user}]
    last_err = ""
    for attempt in range(retries + 1):
        if attempt:
            messages.append({"role": "user",
                             "content": f"That failed validation: {last_err}. Return corrected JSON only."})
        t0 = time.time()
        resp = litellm.completion(
            model=model, messages=messages,
            response_format={"type": "json_object"}, temperature=0,
        )
        raw = resp.choices[0].message.content or ""
        try:
            obj = schema.model_validate_json(_strip_fence(raw))
            print(f"  [{step}] {model} ok ({time.time()-t0:.1f}s)", file=sys.stderr)
            return obj
        except (ValidationError, json.JSONDecodeError) as e:
            last_err = str(e)[:300]
            messages.append({"role": "assistant", "content": raw})
    raise RuntimeError(f"step '{step}' ({model}) failed validation after {retries+1} tries: {last_err}")


def _strip_fence(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1].rsplit("```", 1)[0]
    return s.strip()


def run_pipeline(task: str) -> dict:
    """Fixed 4-step pipeline; each step's OUTPUT is the next step's typed INPUT."""
    plan = run_step("plan", Plan,
                    "You are a senior architect. Plan the implementation.", task)

    code = run_step("code", Code,
                    "You are an expert programmer. Implement the plan exactly.",
                    f"Task: {task}\nPlan: {plan.model_dump_json()}")

    review = run_step("review", Review,
                      "You are a strict code reviewer. Find real bugs only.",
                      f"Task: {task}\nCode:\n{code.source}")

    summary = run_step("summarize", Summary,
                       "Summarise the outcome in one sentence for a PR title.",
                       f"Plan: {plan.approach}\nReview passed: {review.passed}\nIssues: {review.issues}")

    return {
        "task": task,
        "plan": plan.model_dump(),
        "code": code.model_dump(),
        "review": review.model_dump(),
        "summary": summary.model_dump(),
        "routing": STEP_MODELS,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[0]} '<task description>'")
    print(json.dumps(run_pipeline(" ".join(sys.argv[1:])), indent=2))
