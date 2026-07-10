#!/usr/bin/env python3
"""Compress a prompt / RAG context with LLMLingua-2 token pruning.

Usage:
  python compress.py --in context.txt --rate 0.33
  python compress.py --in context.txt --target-token 500 --question "What is the refund policy?"
  cat context.txt | python compress.py --rate 0.5 --json

Requires: pip install llmlingua  (pulls torch + transformers; first run downloads the model)
"""
import argparse
import json
import sys
from typing import Optional


def read_text(path: Optional[str]) -> str:
    if path and path != "-":
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return sys.stdin.read()


def main() -> int:
    ap = argparse.ArgumentParser(description="LLMLingua-2 prompt compressor")
    ap.add_argument("--in", dest="infile", help="Input file (default: stdin)")
    ap.add_argument("--rate", type=float, help="Fraction of tokens to KEEP, e.g. 0.33")
    ap.add_argument("--target-token", type=int, help="Absolute target token count (overrides rate)")
    ap.add_argument("--question", default="", help="Downstream question (token-selection is conditioned on it)")
    ap.add_argument("--model", default="microsoft/llmlingua-2-xlm-roberta-large-meetingbank")
    ap.add_argument("--device", default="cpu", help="cpu | cuda | mps")
    ap.add_argument("--force-tokens", nargs="*", default=["\n", ".", "?", "!", ","],
                    help="Tokens never pruned (protects structure/punctuation)")
    ap.add_argument("--json", action="store_true", help="Emit full stats as JSON")
    args = ap.parse_args()

    if args.rate is None and args.target_token is None:
        args.rate = 0.5  # sane default

    text = read_text(args.infile).strip()
    if not text:
        print("error: empty input", file=sys.stderr)
        return 2

    try:
        from llmlingua import PromptCompressor
    except ImportError:
        print("error: pip install llmlingua", file=sys.stderr)
        return 3

    compressor = PromptCompressor(
        model_name=args.model,
        use_llmlingua2=True,
        device_map=args.device,
    )

    kwargs = dict(
        force_tokens=args.force_tokens,
        drop_consecutive=True,
        question=args.question,
    )
    if args.target_token is not None:
        kwargs["target_token"] = args.target_token
    else:
        kwargs["rate"] = args.rate

    result = compressor.compress_prompt(text, **kwargs)

    if args.json:
        print(json.dumps({
            "compressed_prompt": result["compressed_prompt"],
            "origin_tokens": result.get("origin_tokens"),
            "compressed_tokens": result.get("compressed_tokens"),
            "ratio": result.get("ratio"),
            "rate": result.get("rate"),
            "saving": result.get("saving"),
        }, ensure_ascii=False, indent=2))
    else:
        sys.stderr.write(
            f"[{result.get('origin_tokens')} -> {result.get('compressed_tokens')} tokens, "
            f"{result.get('ratio')}]\n"
        )
        print(result["compressed_prompt"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
