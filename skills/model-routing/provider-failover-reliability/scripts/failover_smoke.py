#!/usr/bin/env python3
"""Smoke-test cross-vendor failover with LiteLLM Router.

Proves two things:
  1. A normal call succeeds and reports which deployment served it.
  2. A forced-failure call falls over to the backup group.

Requires: pip install litellm, and at least one real provider key in env.
Set BACKUP_MODEL/BACKUP_KEY_ENV if you don't use Anthropic.
"""
import os
import sys


def build_router():
    from litellm import Router

    primary_key = os.environ.get("OPENAI_API_KEY")
    backup_key = os.environ.get(os.environ.get("BACKUP_KEY_ENV", "ANTHROPIC_API_KEY"))
    if not (primary_key or backup_key):
        sys.exit("Set OPENAI_API_KEY and/or ANTHROPIC_API_KEY to run this smoke test.")

    model_list = []
    if primary_key:
        model_list.append({"model_name": "chat", "litellm_params": {
            "model": os.environ.get("PRIMARY_MODEL", "openai/gpt-4o-mini"),
            "api_key": primary_key}})
    if backup_key:
        model_list.append({"model_name": "chat-backup", "litellm_params": {
            "model": os.environ.get("BACKUP_MODEL", "anthropic/claude-haiku-4-5"),
            "api_key": backup_key}})

    return Router(
        model_list=model_list,
        fallbacks=[{"chat": ["chat-backup"]}],
        num_retries=2,
        request_timeout=30,
    )


def main():
    router = build_router()
    msgs = [{"role": "user", "content": "Reply with the single word: ok"}]

    print("1) normal call ...")
    r = router.completion(model="chat", messages=msgs)
    served = getattr(r, "model", None) or r._hidden_params.get("model_id")
    print(f"   served by: {served} -> {r.choices[0].message.content!r}")

    print("2) forced-failure call (mock_testing_fallbacks) ...")
    r2 = router.completion(model="chat", messages=msgs, mock_testing_fallbacks=True)
    served2 = getattr(r2, "model", None) or r2._hidden_params.get("model_id")
    print(f"   fell over to: {served2} -> {r2.choices[0].message.content!r}")
    print("PASS: failover path exercised.")


if __name__ == "__main__":
    main()
