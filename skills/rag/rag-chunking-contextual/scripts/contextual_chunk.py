#!/usr/bin/env python3
"""Anthropic Contextual Retrieval, end to end.

Recursively/token-chunks a document, then prepends a Haiku-generated situating
blurb to each chunk (Anthropic's exact prompt), with the full document held in
prompt cache so you pay for it once per document.

Usage:
    ANTHROPIC_API_KEY=... python3 contextual_chunk.py doc.txt [--size 400] [--overlap 60]

Emits JSONL to stdout: {"id","context","chunk","enriched"} per line.
Feed `enriched` to BOTH your embedding model and your BM25 index; keep `chunk`
to return to the LLM if you don't want the blurb in the answer context.

Deps: pip install anthropic tiktoken
"""
import argparse
import json
import os
import sys

MODEL = "claude-haiku-4-5"          # confirm current id against live docs
CTX_TAIL = (
    "\nHere is the chunk we want to situate within the whole document\n"
    "<chunk>\n{chunk}\n</chunk>\n"
    "Please give a short succinct context to situate this chunk within the "
    "overall document for the purposes of improving search retrieval of the "
    "chunk. Answer only with the succinct context and nothing else."
)


def chunk_tokens(text, size, overlap):
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    ids = enc.encode(text)
    step = max(1, size - overlap)
    return [enc.decode(ids[i : i + size]) for i in range(0, len(ids), step)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--size", type=int, default=400)
    ap.add_argument("--overlap", type=int, default=60)
    args = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ERROR: set ANTHROPIC_API_KEY")

    with open(args.path, encoding="utf-8") as fh:
        document = fh.read()
    if not document.strip():
        sys.exit("ERROR: empty document")

    import anthropic
    client = anthropic.Anthropic(api_key=key)
    chunks = chunk_tokens(document, args.size, args.overlap)

    for i, chunk in enumerate(chunks):
        try:
            msg = client.messages.create(
                model=MODEL,
                max_tokens=120,
                messages=[{
                    "role": "user",
                    "content": [
                        {  # cached across every chunk of this document
                            "type": "text",
                            "text": f"<document>\n{document}\n</document>",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": CTX_TAIL.format(chunk=chunk)},
                    ],
                }],
            )
            context = msg.content[0].text.strip()
        except Exception as exc:  # noqa: BLE001 - surface, never silently drop a chunk
            print(f"WARN chunk {i}: {exc}", file=sys.stderr)
            context = ""
        enriched = f"{context}\n\n{chunk}" if context else chunk
        print(json.dumps({
            "id": i, "context": context, "chunk": chunk, "enriched": enriched,
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
