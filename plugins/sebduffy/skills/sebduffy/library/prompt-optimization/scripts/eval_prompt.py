#!/usr/bin/env python3
"""Tiny model-agnostic prompt eval harness for eval-driven prompt hardening.

Usage:
    python eval_prompt.py --prompt prompts/v0.txt --data eval.jsonl --model gpt-4o-mini

Prompt file: plain text. Use {input} as the placeholder for each case's input.
Data file (JSONL), one case per line, any subset of these check keys:
    {"input": "...",                       # required: substituted into the prompt
     "expect_contains":  ["a", "b"],        # all substrings must appear (case-insensitive)
     "forbid_contains":  ["HACKED"],        # none may appear
     "regex":            "^\\{.*\\}$",       # output must match this pattern
     "must_be_json":     true}              # output must parse as JSON

Set OPENAI_API_KEY (default) or ANTHROPIC_API_KEY + --provider anthropic.
"""
import argparse
import json
import os
import re
import sys


def load_cases(path):
    cases = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.exit(f"eval.jsonl line {n} is not valid JSON: {exc}")
            if "input" not in row:
                sys.exit(f"eval.jsonl line {n} missing required 'input' field")
            cases.append(row)
    if not cases:
        sys.exit("No cases found — need at least one row (aim for >=10).")
    return cases


def call_model(provider, model, prompt):
    if provider == "anthropic":
        from anthropic import Anthropic

        resp = Anthropic().messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text
    from openai import OpenAI

    resp = OpenAI().chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


def score(output, case):
    """Return (passed, reason). Deterministic checks only — extend with a judge if needed."""
    low = output.lower()
    for token in case.get("expect_contains", []):
        if token.lower() not in low:
            return False, f"missing expected substring {token!r}"
    for token in case.get("forbid_contains", []):
        if token.lower() in low:
            return False, f"contains forbidden substring {token!r}"
    if "regex" in case and not re.search(case["regex"], output, re.DOTALL):
        return False, f"failed regex {case['regex']!r}"
    if case.get("must_be_json"):
        try:
            json.loads(output)
        except json.JSONDecodeError:
            return False, "not valid JSON"
    return True, "ok"


def main():
    ap = argparse.ArgumentParser(description="Score a prompt over a small eval set.")
    ap.add_argument("--prompt", required=True, help="Prompt template file with {input} placeholder")
    ap.add_argument("--data", required=True, help="JSONL eval cases")
    ap.add_argument("--model", required=True, help="Model id, e.g. gpt-4o-mini or claude-sonnet-4-6")
    ap.add_argument("--provider", default="openai", choices=["openai", "anthropic"])
    args = ap.parse_args()

    template = open(args.prompt, encoding="utf-8").read()
    if "{input}" not in template:
        print("WARN: prompt has no {input} placeholder — every case sends the same prompt.", file=sys.stderr)
    cases = load_cases(args.data)

    passed = 0
    print(f"\n{'#':>2}  {'result':6}  reason")
    print("-" * 60)
    for i, case in enumerate(cases, 1):
        prompt = template.replace("{input}", str(case["input"]))
        try:
            out = call_model(args.provider, args.model, prompt)
        except Exception as exc:  # noqa: BLE001 — surface any SDK/network error per case
            print(f"{i:>2}  {'ERROR':6}  {exc}")
            continue
        ok, reason = score(out, case)
        passed += ok
        print(f"{i:>2}  {'PASS' if ok else 'FAIL':6}  {reason}")

    total = len(cases)
    tag = os.path.splitext(os.path.basename(args.prompt))[0]
    print("-" * 60)
    print(f"{tag}: {passed}/{total} passed ({passed / total:.2f})\n")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
