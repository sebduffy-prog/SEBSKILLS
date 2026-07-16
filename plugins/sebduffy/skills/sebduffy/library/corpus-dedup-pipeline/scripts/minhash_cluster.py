#!/usr/bin/env python3
"""Fuzzy near-dup clustering via MinHash + LSH + union-find.

Reads one JSON record per line from stdin (or a file arg): {"id": ..., "text": ...}.
Writes one JSON line per surviving representative to stdout, plus a cluster map
to --clusters PATH. Deterministic given num_perm/seed. Pure datasketch + stdlib.

Usage:
  python3 minhash_cluster.py corpus.jsonl --threshold 0.8 --num-perm 128 \
      --shingle 3 --clusters clusters.json > kept.jsonl
"""
import argparse, json, re, sys
from datasketch import MinHash, MinHashLSH

WORD = re.compile(r"\w+", re.UNICODE)


def shingles(text, k):
    toks = WORD.findall(text.lower())
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def signature(text, k, num_perm):
    m = MinHash(num_perm=num_perm)
    for sh in shingles(text, k):
        m.update(sh.encode("utf-8"))
    return m


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("infile", nargs="?", default="-")
    ap.add_argument("--threshold", type=float, default=0.8)
    ap.add_argument("--num-perm", type=int, default=128)
    ap.add_argument("--shingle", type=int, default=3)
    ap.add_argument("--clusters", default=None)
    a = ap.parse_args()

    fh = sys.stdin if a.infile == "-" else open(a.infile, encoding="utf-8")
    records, sigs = [], {}
    lsh = MinHashLSH(threshold=a.threshold, num_perm=a.num_perm)
    uf = UnionFind()

    for i, line in enumerate(fh):
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        rid = rec.get("id", i)
        m = signature(rec.get("text", ""), a.shingle, a.num_perm)
        for cand in lsh.query(m):  # candidates already inserted
            uf.union(rid, cand)
        lsh.insert(rid, m)
        uf.find(rid)  # register singletons
        sigs[rid] = m
        records.append((rid, rec))

    clusters = {}
    for rid, _ in records:
        clusters.setdefault(uf.find(rid), []).append(rid)

    kept_roots = set(clusters)
    for rid, rec in records:
        if rid in kept_roots:
            sys.stdout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    if a.clusters:
        with open(a.clusters, "w", encoding="utf-8") as out:
            json.dump({str(k): v for k, v in clusters.items()}, out, ensure_ascii=False, indent=2)

    sys.stderr.write(
        f"in={len(records)} kept={len(clusters)} removed={len(records)-len(clusters)}\n"
    )


if __name__ == "__main__":
    main()
