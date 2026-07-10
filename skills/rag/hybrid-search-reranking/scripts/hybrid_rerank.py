#!/usr/bin/env python3
"""End-to-end local hybrid retrieval: BM25 + dense ANN -> RRF -> cross-encoder rerank.

Pure-Python, no vector DB. Good for prototyping on an in-memory corpus and for unit-testing
the fusion + rerank logic. Swap the retrievers for a real vector DB (see Recipe B) in prod.

Deps (all optional at import time so RRF stays unit-testable with none installed):
    pip install rank_bm25 sentence-transformers
Reranker: local CrossEncoder (default) or Cohere if COHERE_API_KEY + `pip install cohere`.

Usage:
    python hybrid_rerank.py "your query here"
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict

RRF_K = 60          # rank-fusion smoothing constant (lower = sharper top-rank weight)
FIRST_STAGE_K = 25  # candidates pulled from EACH retriever before fusion
FINAL_TOP_N = 5     # kept after rerank


def reciprocal_rank_fusion(ranked_lists, k=RRF_K):
    """ranked_lists: list of lists of doc ids, each best-first. Returns [(id, score)] best-first."""
    scores = defaultdict(float)
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] += 1.0 / (k + rank + 1)  # +1 -> 1-based rank
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def bm25_rank(query, corpus, top_k=FIRST_STAGE_K):
    from rank_bm25 import BM25Okapi

    tokenized = [d.lower().split() for d in corpus]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(query.lower().split())
    order = sorted(range(len(corpus)), key=lambda i: scores[i], reverse=True)
    return [str(i) for i in order[:top_k]]


def dense_rank(query, corpus, encoder, top_k=FIRST_STAGE_K):
    import numpy as np

    doc_emb = encoder.encode(corpus, normalize_embeddings=True)
    q_emb = encoder.encode([query], normalize_embeddings=True)[0]
    sims = doc_emb @ q_emb  # cosine (unit vectors)
    order = np.argsort(-sims)
    return [str(i) for i in order[:top_k]]


def rerank(query, docs, top_n=FINAL_TOP_N):
    """Return [(doc, score)] best-first. Cohere if key present, else local cross-encoder."""
    if os.getenv("COHERE_API_KEY"):
        import cohere

        co = cohere.ClientV2()
        r = co.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=top_n)
        return [(docs[o.index], o.relevance_score) for o in r.results]

    from sentence_transformers import CrossEncoder

    ce = CrossEncoder("BAAI/bge-reranker-v2-m3")
    scores = ce.predict([(query, d) for d in docs])
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:top_n]
    return [(docs[i], float(scores[i])) for i in order]


def hybrid_search(query, corpus, encoder):
    bm25_ids = bm25_rank(query, corpus)
    dense_ids = dense_rank(query, corpus, encoder)
    fused = reciprocal_rank_fusion([bm25_ids, dense_ids])
    candidates = [corpus[int(doc_id)] for doc_id, _ in fused]
    return rerank(query, candidates)


def _demo(query):
    from sentence_transformers import SentenceTransformer

    corpus = [
        "The error code E-4021 means the payment gateway timed out.",
        "Reset your password from the account settings page.",
        "Gateway timeouts are usually transient; retry after 30 seconds.",
        "Our refund policy allows returns within 30 days of purchase.",
        "To rotate an API key, open the developer dashboard.",
    ]
    encoder = SentenceTransformer("BAAI/bge-small-en-v1.5")
    for doc, score in hybrid_search(query, corpus, encoder):
        print(f"{score:.4f}  {doc}")


if __name__ == "__main__":
    _demo(sys.argv[1] if len(sys.argv) > 1 else "why did payment E-4021 fail")
