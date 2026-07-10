#!/usr/bin/env python3
"""Fold a facts.jsonl working-memory file: dedup near-identical claims and surface
contradictions. Stdlib only (python3.9+). Mechanical helper for step 3 of the
long-horizon-research-agent harness — the LLM still writes core.md, this just does
the deterministic dedup/merge pass so it is reproducible and cheap.

Usage:  python3 fold_memory.py runs/<slug>/memory/facts.jsonl [--out folded.jsonl]

Each input line is a JSON object: {id, text, value?, source_url, subtopic?, confidence?}
Output: deduped claims (highest confidence kept, source_urls unioned) + a contradiction
report printed to stderr. Deduped JSONL goes to --out (default: <input>.folded.jsonl).
"""
import argparse
import json
import re
import sys
from difflib import SequenceMatcher

SIMILARITY_THRESHOLD = 0.87  # text similarity above which two claims are "the same claim"


def normalize(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def load_facts(path):
    facts = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                sys.exit(f"error: {path}:{lineno} is not valid JSON: {exc}")
            if "text" not in obj:
                sys.exit(f"error: {path}:{lineno} missing required 'text' field")
            facts.append(obj)
    return facts


def fold(facts):
    """Cluster by text similarity. Returns (deduped, contradictions)."""
    clusters = []  # each: {"norm": str, "members": [fact, ...]}
    for fact in facts:
        norm = normalize(fact["text"])
        placed = False
        for cluster in clusters:
            if similar(norm, cluster["norm"]) >= SIMILARITY_THRESHOLD:
                cluster["members"].append(fact)
                placed = True
                break
        if not placed:
            clusters.append({"norm": norm, "members": [fact]})

    deduped, contradictions = [], []
    for cluster in clusters:
        members = cluster["members"]
        best = max(members, key=lambda m: float(m.get("confidence", 0) or 0))
        urls = sorted({m.get("source_url") for m in members if m.get("source_url")})
        merged = dict(best)
        merged["source_url"] = urls
        merged["support_count"] = len(members)
        deduped.append(merged)
        # contradiction: same claim, differing non-empty 'value'
        values = {str(m["value"]) for m in members if m.get("value") not in (None, "")}
        if len(values) > 1:
            contradictions.append({"text": best["text"], "values": sorted(values)})
    return deduped, contradictions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("facts", help="path to facts.jsonl")
    ap.add_argument("--out", help="output deduped jsonl path")
    args = ap.parse_args()

    facts = load_facts(args.facts)
    deduped, contradictions = fold(facts)

    out_path = args.out or (args.facts + ".folded.jsonl")
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in deduped:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"in={len(facts)} deduped={len(deduped)} contradictions={len(contradictions)} -> {out_path}")
    for c in contradictions:
        print(f"  CONTRADICTION: {c['text']!r} has values {c['values']}", file=sys.stderr)
    # non-zero exit signals unresolved contradictions the orchestrator must reconcile
    sys.exit(1 if contradictions else 0)


if __name__ == "__main__":
    main()
