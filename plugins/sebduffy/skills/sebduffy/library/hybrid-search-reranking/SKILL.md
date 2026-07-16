---
name: hybrid-search-reranking
category: rag
description: >
  Build two-stage retrieval that fixes both recall and precision: fuse BM25/sparse lexical
  search with dense ANN vectors using Reciprocal Rank Fusion (rank-based, no score
  normalization), then rerank the fused top-k with a cross-encoder (Cohere Rerank, Voyage,
  Jina, or a local BGE cross-encoder) to sort by true relevance. Use when RAG "misses the
  obvious answer", when keyword-only or vector-only search underperforms, or when you ask
  "hybrid search", "combine BM25 and embeddings", "reciprocal rank fusion", "RRF", "add a
  reranker", "cross-encoder rerank", "Cohere rerank", "why is my top result wrong".
when_to_use:
  - "Vector-only retrieval misses exact terms (product codes, names, acronyms) that BM25 would nail"
  - "BM25-only search misses paraphrases/synonyms that embeddings would catch — you want both"
  - "The right chunk is retrieved but ranked #7; you need it at #1 before it hits the LLM context"
  - "You ask how to combine lexical + dense results without normalizing incompatible score scales"
  - "Setting up production retrieval and want the standard recall-then-precision two-stage pattern"
  - "Choosing/pricing a reranker (Cohere vs Voyage vs Jina vs a local BGE cross-encoder)"
when_not_to_use:
  - "Deciding chunk size/strategy or adding context to chunks before embedding — use rag-chunking-contextual"
  - "Entity/relationship graph traversal over the corpus — use graphrag-builder"
  - "Measuring whether retrieval/answers improved (recall@k, nDCG, faithfulness) — use llm-rag-eval-harness"
  - "Multi-step tool-using retrieval agents that plan their own queries — use agentic-rag-pipeline"
  - "Standing up the vector DB / collection / index itself — use vector-store-setup"
keywords: [hybrid search, bm25, dense retrieval, reciprocal rank fusion, rrf, reranker, rerank, cross-encoder, cohere rerank, voyage rerank, jina reranker, bge reranker, sparse vector, splade, two-stage retrieval, fusion, recall precision, qdrant fusion, weaviate hybrid, retrieval]
similar_to: [rag-chunking-contextual, graphrag-builder, llm-rag-eval-harness, agentic-rag-pipeline, vector-store-setup, retrieval-as-context, long-doc-chunking]
inputs_needed:
  - Where the candidates come from — a vector DB with a fusion API (Qdrant/Weaviate) or two separate result lists (BM25 + ANN) you fuse yourself
  - Corpus size (sets the RRF k and the first-stage top-k you pull before reranking)
  - Reranker choice + budget — hosted API (Cohere/Voyage/Jina, needs an API key) or a local cross-encoder (GPU-friendly, no per-call cost)
produces: A retrieve→fuse→rerank pipeline (RRF over BM25+dense, then a cross-encoder returning top_n) with runnable Python
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Hybrid Search + Reranking (two-stage retrieval)

Single-retriever RAG leaks in two places. **Recall:** dense vectors miss exact tokens (SKUs,
error codes, surnames); BM25 misses paraphrases. **Precision:** even when the right chunk is in
the top-k, a bi-encoder ranks it poorly because query and doc were embedded independently. The
fix is two stages:

1. **Recall — hybrid + fuse.** Run BM25 (lexical) and dense ANN (semantic) in parallel, take
   top ~20–50 from each, and fuse with **Reciprocal Rank Fusion (RRF)** into one candidate list.
2. **Precision — rerank.** Feed the fused candidates (query + each doc together) to a
   **cross-encoder** reranker; keep its `top_n` for the LLM context.

## When to use

- Retrieval "misses the obvious answer," or the correct chunk lands mid-list, not at #1.
- Keyword-only or vector-only search each fail on a slice of queries and you want the union.
- You need production-grade retrieval and want the standard, boring, effective pattern.

## Prerequisites

- **Candidates.** Either a vector DB with a native fusion query (Qdrant `FusionQuery`, Weaviate
  `hybrid`, Elasticsearch/OpenSearch `rrf`), or two plain result lists you fuse in Python.
- **Sparse side.** BM25 via the DB, or `rank_bm25` / a SPLADE sparse model locally.
- **Reranker, pick one:**
  - Cohere — `pip install cohere`, `COHERE_API_KEY`. Model `rerank-v3.5` (v4 tier: `rerank-v4.0-pro`), 4096-token context, 100+ languages, ≤1000 docs/call.
  - Voyage — `pip install voyageai`, `VOYAGE_API_KEY`. Model `rerank-2.5` (or `rerank-2.5-lite`).
  - Jina — HTTP `POST https://api.jina.ai/v1/rerank`, `JINA_API_KEY`. Model `jina-reranker-v2-base-multilingual` (or `jina-reranker-v3`).
  - Local — `pip install sentence-transformers`, `BAAI/bge-reranker-v2-m3` (no API cost, wants a GPU).

`pip install qdrant-client sentence-transformers rank_bm25 cohere` covers the examples below.

## Recipe A — RRF you control (two lists → one)

Use when your BM25 and ANN results are just two Python lists. RRF works on **ranks**, so it
sidesteps the fact that BM25 scores and cosine similarities live on incompatible scales — no
normalization, no tuning weights. Formula: `score(d) = Σ 1/(k + rank_i(d))` over each list where
`d` appears (`rank` is 0-based here, so add 1).

```python
from collections import defaultdict

def reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """ranked_lists: each is doc_ids best-first. Returns (doc_id, score) best-first."""
    scores: dict[str, float] = defaultdict(float)
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked):
            scores[doc_id] += 1.0 / (k + rank + 1)   # +1 → 1-based rank
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

bm25_ids = ["d5", "d1", "d9", "d3"]   # lexical, best-first
dense_ids = ["d9", "d2", "d5", "d7"]  # semantic, best-first
fused = reciprocal_rank_fusion([bm25_ids, dense_ids], k=60)
# d5 and d9 (in both lists) float to the top; k smooths the rank-1 dominance.
```

**Choosing k.** `k=60` is the paper default (Cormack et al., SIGIR 2009), tuned for TREC-scale
corpora. Smaller `k` sharpens the weight of top ranks; for a 100–300 page knowledge base try
`k=10..20`. Larger `k` flattens toward a democratic vote. Pull top **20–50** from each retriever
before fusing — enough that a good doc missing from one list survives via the other.

`scripts/hybrid_rerank.py` wraps A end-to-end (BM25 + a dense encoder + RRF + rerank) for local corpora.

## Recipe B — let the vector DB fuse (Qdrant Query API)

Qdrant does BM25/sparse + dense + RRF in one round-trip via `prefetch` + `FusionQuery`. No
manual RRF, no second network hop for candidates.

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")
q_dense  = dense_model.encode(query).tolist()                 # e.g. bge / voyage / openai
q_sparse = models.SparseVector(indices=idx, values=vals)      # SPLADE / bm42 / bm25 sparse

hits = client.query_points(
    collection_name="docs",
    prefetch=[
        models.Prefetch(query=q_sparse, using="sparse", limit=25),
        models.Prefetch(query=q_dense,  using="dense",  limit=25),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),   # or Fusion.DBSF for score-based fusion
    limit=25,          # fused candidates to hand to the reranker
    with_payload=True,
).points
```

`Fusion.RRF` = rank-based (robust default). `Fusion.DBSF` = distribution-based score fusion
(normalizes each retriever's scores by mean±std, then sums) — try it when both retrievers
produce well-calibrated scores. Weaviate's equivalent is `collection.query.hybrid(query=...,
alpha=0.5)` (`alpha` 0=pure keyword, 1=pure vector); Elasticsearch/OpenSearch expose an `rrf`
retriever. Prefer the DB's native fusion over hand-rolled RRF when you have it.

## Recipe C — rerank the fused candidates (the precision stage)

A cross-encoder scores `(query, doc)` **jointly**, so it sees interactions a bi-encoder can't.
It's slow per pair — that's exactly why it runs on ~25 candidates, not the whole corpus.

**Cohere** (`co.rerank` returns results sorted by `relevance_score`, each with an `index` back
into your input list — you must map indices to your docs):

```python
import cohere
co = cohere.ClientV2()  # reads COHERE_API_KEY

docs = [h.payload["text"] for h in hits]          # fused candidate texts
r = co.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=5)
top = [(hits[o.index], o.relevance_score) for o in r.results]   # map index → original hit
```

Raw HTTP equivalent: `POST https://api.cohere.com/v2/rerank`, `Authorization: Bearer $COHERE_API_KEY`,
body `{"model":"rerank-v3.5","query":...,"documents":[...],"top_n":5}`.

**Voyage:** `voyageai.Client().rerank(query, docs, model="rerank-2.5", top_k=5)` →
`.results[i].index` / `.relevance_score`. **Jina:** POST the same shape to
`https://api.jina.ai/v1/rerank` with `model="jina-reranker-v2-base-multilingual"`.

**Local BGE cross-encoder** (no API key, no per-call cost):

```python
from sentence_transformers import CrossEncoder
ce = CrossEncoder("BAAI/bge-reranker-v2-m3")
pairs  = [(query, d) for d in docs]
scores = ce.predict(pairs)                         # higher = more relevant
order  = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:5]
top    = [(hits[i], float(scores[i])) for i in order]
```

Then build the LLM context from `top` only. Typical shape: retrieve 20–50 per retriever → fuse →
rerank → keep **top 3–8**.

## Verify

- **A/B the stages.** Hold a set of queries with known-correct chunks. Measure recall@k after
  fusion (should beat either single retriever) and nDCG@k / MRR after rerank (should beat fusion
  alone). Use `llm-rag-eval-harness` for the harness.
- **Fusion sanity:** a doc appearing in *both* lists should outrank one that's rank-1 in only
  one list, for reasonable `k`. Print pre- and post-fusion orders on a known query.
- **Rerank sanity:** the reranker should reorder — if the post-rerank order equals the input
  order on every query, check you're mapping `result.index` back to the right doc.
- Latency budget: BM25 + ANN are ms; the rerank call dominates. Cap candidates (≤50) and cache.

## Pitfalls

- **Normalizing scores to "fuse" them.** BM25 vs cosine scales aren't comparable; min-max
  hacks are brittle. That's the whole reason RRF operates on ranks — don't reintroduce the
  problem.
- **Forgetting the index→doc mapping.** Every hosted reranker returns positions into the array
  you sent, not your original IDs. Re-key against the candidate list or you'll cite the wrong
  chunk.
- **Reranking the whole corpus.** Cross-encoders are O(candidates) network/compute — they're a
  precision filter over a small fused set, never a first-stage retriever.
- **Pulling too few first-stage candidates.** If you fetch top-5 from each retriever, the
  reranker can't rescue a doc that sat at rank 8. Give it 20–50.
- **Wrong `k` for corpus size.** `k=60` on a tiny KB over-flattens; drop to 10–20. Re-tune when
  the corpus grows by an order of magnitude.
- **Reranker context truncation.** Long chunks get cut to the model's limit (Cohere 4096,
  Jina v2 1024 tokens) — the reranker only scores what it sees. Keep rerank inputs tight or use
  a long-context reranker (`jina-reranker-v3`, 131k).
- **Stale model names.** Rerankers version fast (Cohere v3.5→v4, Voyage 2.5, Jina v3). Confirm
  the current model id in the vendor docs before shipping.
