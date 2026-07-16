#!/usr/bin/env python3
"""N-gram contamination check for eval sets — the HELM / GPT-3 default screen.

Flags eval items whose normalised text shares an n-gram (default 13, the GPT-3
threshold; HELM uses the same family) with ANY document in a reference corpus
(training data, web dump, prior eval versions). Pure stdlib, streams the corpus
line-by-line so a multi-GB reference file never lands in memory at once.

This catches VERBATIM and near-verbatim leakage. It does NOT catch rephrased /
translated leakage — for that add the LLM-decontaminator pass (see SKILL.md).

Usage:
  python3 contamination_ngram.py --eval eval.jsonl --ref train.txt [--n 13] \
      [--field question] [--threshold 1] [--out flagged.jsonl]

--eval : JSONL, one object per line (or plain .txt, one item per line).
--ref  : reference corpus. .jsonl (uses --field or whole line) or .txt.
--n    : n-gram size in WORDS (default 13).
--threshold : min number of distinct shared n-grams to flag (default 1).
"""
import argparse
import json
import re
import sys

WORD_RE = re.compile(r"[a-z0-9]+")


def normalise(text):
    """Lowercase, strip punctuation, collapse whitespace to a word list."""
    return WORD_RE.findall(text.lower())


def ngrams(words, n):
    if len(words) < n:
        # Short items: use the whole item as a single gram so they are still
        # comparable (a 4-word answer can still be leaked verbatim).
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + n]) for i in range(len(words) - n + 1)}


def read_items(path, field):
    """Yield (index, raw_obj, text) from a .jsonl or .txt file."""
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            if path.endswith(".jsonl") or path.endswith(".json"):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    print(f"warn: bad JSON at {path}:{i+1}", file=sys.stderr)
                    continue
                text = obj.get(field, "") if field else json.dumps(obj)
                if not text and field:
                    # fall back to concatenating string values
                    text = " ".join(str(v) for v in obj.values() if isinstance(v, str))
                yield i, obj, text
            else:
                yield i, {"text": line}, line


def build_ref_index(ref_path, field, n):
    """Return set of every n-gram seen anywhere in the reference corpus."""
    seen = set()
    for _, _, text in read_items(ref_path, field):
        seen |= ngrams(normalise(text), n)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--n", type=int, default=13)
    ap.add_argument("--field", default="question")
    ap.add_argument("--threshold", type=int, default=1)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ref_grams = build_ref_index(args.ref, args.field, args.n)
    print(f"reference: {len(ref_grams):,} distinct {args.n}-grams", file=sys.stderr)

    total = 0
    flagged = []
    for idx, obj, text in read_items(args.eval, args.field):
        total += 1
        overlap = ngrams(normalise(text), args.n) & ref_grams
        if len(overlap) >= args.threshold:
            flagged.append(
                {
                    "index": idx,
                    "shared_ngrams": len(overlap),
                    "example": next(iter(overlap)),
                    "item": obj,
                }
            )

    rate = (len(flagged) / total * 100) if total else 0.0
    print(f"eval items: {total}", file=sys.stderr)
    print(f"FLAGGED (>= {args.threshold} shared {args.n}-gram): "
          f"{len(flagged)} ({rate:.1f}%)", file=sys.stderr)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            for row in flagged:
                fh.write(json.dumps(row) + "\n")
        print(f"wrote {args.out}", file=sys.stderr)
    else:
        for row in flagged[:20]:
            print(json.dumps(row))

    # Non-zero exit when anything is contaminated — usable as a CI gate.
    sys.exit(1 if flagged else 0)


if __name__ == "__main__":
    main()
