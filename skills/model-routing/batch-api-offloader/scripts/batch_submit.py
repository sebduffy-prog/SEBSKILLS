#!/usr/bin/env python3
"""Submit a batch of prompts to Anthropic or OpenAI Batch API, poll, and reconcile by custom_id.

Input:  JSONL, one object per line: {"id": "<unique>", "prompt": "<text>"}
Output: results.jsonl, one object per line: {"id": ..., "status": ..., "text"/"error": ...}

Usage:
  export ANTHROPIC_API_KEY=... ; python3 batch_submit.py --provider anthropic \
      --model claude-sonnet-4-5 --in items.jsonl --out results.jsonl
  export OPENAI_API_KEY=...    ; python3 batch_submit.py --provider openai \
      --model gpt-4.1-mini --in items.jsonl --out results.jsonl
"""
import argparse
import json
import re
import sys
import time

POLL_SECONDS = 30
MAX_TOKENS = 512
ID_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def load_items(path):
    items = []
    with open(path) as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "id" not in obj or "prompt" not in obj:
                sys.exit(f"line {lineno}: each item needs 'id' and 'prompt'")
            items.append(obj)
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        sys.exit("duplicate ids found; custom_id must be unique within a batch")
    return items


def run_anthropic(items, model, out_path):
    import anthropic

    client = anthropic.Anthropic()
    for it in items:
        if not ID_RE.match(str(it["id"])):
            sys.exit(f"id {it['id']!r} violates Anthropic ^[a-zA-Z0-9_-]{{1,64}}$")
    requests = [
        {
            "custom_id": str(it["id"]),
            "params": {
                "model": model,
                "max_tokens": MAX_TOKENS,
                "messages": [{"role": "user", "content": it["prompt"]}],
            },
        }
        for it in items
    ]
    batch = client.messages.batches.create(requests=requests)
    print(f"submitted {batch.id} ({len(requests)} requests)", file=sys.stderr)
    while True:
        b = client.messages.batches.retrieve(batch.id)
        if b.processing_status == "ended":
            break
        print(f"  {b.processing_status} {b.request_counts}", file=sys.stderr)
        time.sleep(POLL_SECONDS)
    with open(out_path, "w") as f:
        for r in client.messages.batches.results(batch.id):
            rec = {"id": r.custom_id, "status": r.result.type}
            if r.result.type == "succeeded":
                rec["text"] = r.result.message.content[0].text
            elif r.result.type == "errored":
                rec["error"] = str(r.result.error.type)
            f.write(json.dumps(rec) + "\n")


def run_openai(items, model, out_path):
    from openai import OpenAI

    client = OpenAI()
    in_path = out_path + ".batch_in.jsonl"
    with open(in_path, "w") as f:
        for it in items:
            f.write(
                json.dumps(
                    {
                        "custom_id": str(it["id"]),
                        "method": "POST",
                        "url": "/v1/chat/completions",
                        "body": {
                            "model": model,
                            "messages": [{"role": "user", "content": it["prompt"]}],
                            "max_tokens": MAX_TOKENS,
                        },
                    }
                )
                + "\n"
            )
    up = client.files.create(file=open(in_path, "rb"), purpose="batch")
    batch = client.batches.create(
        input_file_id=up.id, endpoint="/v1/chat/completions", completion_window="24h"
    )
    print(f"submitted {batch.id} ({len(items)} requests)", file=sys.stderr)
    terminal = {"completed", "failed", "expired", "cancelled"}
    while True:
        b = client.batches.retrieve(batch.id)
        if b.status in terminal:
            break
        print(f"  {b.status} {b.request_counts}", file=sys.stderr)
        time.sleep(POLL_SECONDS)
    with open(out_path, "w") as f:
        for file_id, ok in ((b.output_file_id, True), (b.error_file_id, False)):
            if not file_id:
                continue
            for line in client.files.content(file_id).text.splitlines():
                r = json.loads(line)
                rec = {"id": r["custom_id"]}
                if ok and r.get("error") is None and r["response"]["status_code"] == 200:
                    rec["status"] = "succeeded"
                    rec["text"] = r["response"]["body"]["choices"][0]["message"]["content"]
                else:
                    rec["status"] = "errored"
                    rec["error"] = str(r.get("error"))
                f.write(json.dumps(rec) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--provider", required=True, choices=["anthropic", "openai"])
    p.add_argument("--model", required=True)
    p.add_argument("--in", dest="in_path", required=True, help="input JSONL of {id, prompt}")
    p.add_argument("--out", dest="out_path", default="results.jsonl")
    args = p.parse_args()

    items = load_items(args.in_path)
    if args.provider == "anthropic":
        run_anthropic(items, args.model, args.out_path)
    else:
        run_openai(items, args.model, args.out_path)
    print(f"wrote {args.out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
