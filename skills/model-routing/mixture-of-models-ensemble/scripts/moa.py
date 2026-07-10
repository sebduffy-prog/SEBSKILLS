#!/usr/bin/env python3
"""Minimal Mixture-of-Agents ensemble across vendors.

Ported/adapted from togethercomputer/MoA (Apache-2.0) — see LICENSE.
Fans one prompt to N proposer models (any OpenAI-compatible endpoint),
then has one aggregator model synthesize a single better answer.

Usage:
  export OPENAI_API_KEY=...          # for OpenAI-hosted proposers/aggregator
  export TOGETHER_API_KEY=...        # optional, for Together-hosted models
  python3 moa.py "Explain CRDTs to a backend engineer in 6 bullets."

Deps: pip install openai>=1.0
"""
import argparse
import concurrent.futures as cf
import os
import sys

try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install 'openai>=1.0' first")

# Verbatim aggregator system prompt from togethercomputer/MoA (Apache-2.0).
AGGREGATOR_SYSTEM = """You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.

Responses from models:"""

# Each entry: (base_url_env_or_None, api_key_env, model_id).
# None base_url => default OpenAI endpoint. Swap freely for cross-vendor mixes.
TOGETHER_URL = "https://api.together.xyz/v1"
DEFAULT_PROPOSERS = [
    (None, "OPENAI_API_KEY", "gpt-4o-mini"),
    (TOGETHER_URL, "TOGETHER_API_KEY", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    (TOGETHER_URL, "TOGETHER_API_KEY", "Qwen/Qwen2.5-72B-Instruct-Turbo"),
]
DEFAULT_AGGREGATOR = (None, "OPENAI_API_KEY", "gpt-4o")


def client_for(base_url_env, key_env):
    key = os.environ.get(key_env)
    if not key:
        raise RuntimeError(f"missing env {key_env}")
    return OpenAI(api_key=key, base_url=base_url_env) if base_url_env else OpenAI(api_key=key)


def ask(spec, messages, temperature=0.7, max_tokens=2048):
    base_url, key_env, model = spec
    resp = client_for(base_url, key_env).chat.completions.create(
        model=model, messages=messages, temperature=temperature, max_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def inject_references(user_prompt, references):
    """Build aggregator messages: MoA-style numbered reference list."""
    system = AGGREGATOR_SYSTEM
    for i, ref in enumerate(references):
        system += f"\n{i+1}. {ref}"
    return [{"role": "system", "content": system},
            {"role": "user", "content": user_prompt}]


def moa(prompt, proposers=DEFAULT_PROPOSERS, aggregator=DEFAULT_AGGREGATOR):
    msgs = [{"role": "user", "content": prompt}]
    refs = []
    with cf.ThreadPoolExecutor(max_workers=len(proposers)) as ex:
        futs = {ex.submit(ask, p, msgs): p for p in proposers}
        for fut in cf.as_completed(futs):
            try:
                refs.append(fut.result())
            except Exception as e:  # a dead proposer must not sink the ensemble
                sys.stderr.write(f"[warn] proposer {futs[fut][2]} failed: {e}\n")
    if not refs:
        raise RuntimeError("all proposers failed; nothing to aggregate")
    return ask(aggregator, inject_references(prompt, refs), temperature=0.3), refs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--show-drafts", action="store_true")
    args = ap.parse_args()
    final, drafts = moa(args.prompt)
    if args.show_drafts:
        for i, d in enumerate(drafts):
            print(f"\n=== draft {i+1} ===\n{d}", file=sys.stderr)
    print(final)
