---
name: vector-store-setup
category: rag
description: >
  Pick, provision, and tune the vector store under a RAG app — pgvector, Qdrant, Chroma, or
  LanceDB. Chooses the right engine for the scale, writes the schema/collection, sets HNSW or
  IVFFlat/IVF_PQ index params (m, ef_construction, lists, num_partitions), wires metadata
  filtering so it stays fast, and gives the migrate-when-you-outgrow-it thresholds. Use when
  you ask "which vector DB", "set up pgvector", "create a Qdrant collection", "HNSW vs IVFFlat",
  "tune ef_search / ef_construction", "filtered vector search is slow", "my index won't fit in
  RAM", "should I move off Chroma", or "add an embedding column to Postgres".
when_to_use:
  - "Standing up a brand-new vector store and unsure whether to use pgvector, Qdrant, Chroma, or LanceDB"
  - "You have Postgres already and want to add vector search without running a second database"
  - "Choosing/tuning the index — HNSW vs IVFFlat vs IVF_PQ, and what m / ef_construction / lists to set"
  - "Filtered vector search (by tenant, date, category) is slow or returns too few results"
  - "Recall is bad or queries are slow and you need to know which knob (ef_search, nprobes) to turn"
  - "You've outgrown Chroma/an in-process store and need the threshold + steps to migrate to Qdrant/pgvector"
  - "The index no longer fits in RAM and you need on-disk / quantization options"
when_not_to_use:
  - "Deciding chunk size or adding context to chunks before embedding — use rag-chunking-contextual"
  - "Combining BM25 + dense and adding a reranker on top of an existing store — use hybrid-search-reranking"
  - "Building an entity/relationship graph over the corpus — use graphrag-builder"
  - "Measuring whether retrieval improved (recall@k, nDCG) — use llm-rag-eval-harness"
  - "Orchestrating multi-step tool-using retrieval agents — use agentic-rag-pipeline"
keywords: [vector database, vector store, pgvector, qdrant, chroma, chromadb, lancedb, hnsw, ivfflat, ivf_pq, ef_construction, ef_search, m parameter, num_partitions, metadata filtering, payload index, embedding column, ann index, cosine distance, halfvec, quantization, on-disk vectors, vector db migration]
similar_to: [rag-chunking-contextual, hybrid-search-reranking, graphrag-builder, llm-rag-eval-harness, agentic-rag-pipeline, retrieval-as-context, long-doc-chunking]
inputs_needed:
  - Corpus size now and projected (rows), and embedding dimension (e.g. 1536, 3072) — drives engine + index choice
  - Do you already run Postgres? (tilts toward pgvector) and is filtering by metadata required?
  - Distance metric the embedding model expects (cosine for OpenAI/most; L2/inner-product for some)
  - Deployment target — single box / serverless / managed, and RAM budget vs corpus size
produces: A provisioned vector store (schema or collection) with a tuned ANN index, metadata filtering, and query params
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Vector Store Setup (pick, provision, tune)

The store choice is mostly a function of **scale** and **whether you already run Postgres**.
Everything below assumes you already have embeddings (a vector per chunk) and just need
somewhere to put them that returns nearest neighbours fast and lets you filter by metadata.

## When to use

- Starting a RAG app and need to stand up the store — or the current one is slow / too small.
- Deciding the index type and the two or three params that actually matter.
- Fixing slow *filtered* search, bad recall, or an index that won't fit in RAM.

## Pick the engine (decision rule)

| Situation | Use | Why |
|---|---|---|
| You already run Postgres; ≤ ~5–10M vectors | **pgvector** | One database, transactions, SQL joins with your metadata. |
| Need best filtered-search perf, sparse+dense, sharding, >10M | **Qdrant** | Filter-aware HNSW, payload indexes, quantization, horizontal scale. |
| Prototype / notebook / small local app (< ~1M) | **Chroma** | Zero-ops in-process; embed-and-go. Migrate when it hurts. |
| Embedded/analytical, versioned data, columnar, huge but disk-bound | **LanceDB** | On-disk Lance columnar format, no server, scales past RAM. |

Rule of thumb: **default to pgvector if you have Postgres**, reach for **Qdrant** when filtering
or scale becomes the bottleneck, start in **Chroma** only for throwaway prototypes.

## Prerequisites

- Python 3.9+. Install only the client you picked:
  `pip install pgvector psycopg[binary]` · `pip install qdrant-client` · `pip install chromadb` · `pip install lancedb`
- Distance metric must match your embedding model: OpenAI `text-embedding-3-*`, Cohere, and most
  modern models are **cosine**. Using the wrong metric silently wrecks recall.
- pgvector needs the extension available on the server (`CREATE EXTENSION vector;` — bundled with
  most managed Postgres; on RDS/Aurora/Neon/Supabase it's a one-line enable).

## Recipe A — pgvector

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
  id         bigserial PRIMARY KEY,
  doc_id     text NOT NULL,
  category   text,
  created_at timestamptz DEFAULT now(),
  content    text,
  embedding  vector(1536)        -- match your model's dim; use halfvec(3072) for large dims
);

-- HNSW index (default choice: better recall/latency, no training step)
CREATE INDEX ON chunks USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- B-tree indexes on anything you FILTER by, so the planner can pre-filter
CREATE INDEX ON chunks (category);
CREATE INDEX ON chunks (doc_id);
```

Query (cosine distance = `<=>`; `<->` L2, `<#>` inner product):

```sql
SET hnsw.ef_search = 100;                 -- raise for recall, lower for speed (default 40)
SELECT id, content, 1 - (embedding <=> :q) AS score
FROM chunks
WHERE category = 'faq'                     -- pgvector filters, then walks the graph
ORDER BY embedding <=> :q
LIMIT 10;
```

Notes that bite people:
- **`vector` index caps at 2000 dims.** For 3072-dim models store `halfvec(3072)` and index with
  `halfvec_cosine_ops` (half precision, negligible recall loss, half the size).
- **HNSW vs IVFFlat:** prefer HNSW. IVFFlat needs data present before you build it and needs a
  `lists` value (`rows/1000` up to 1M rows, then `sqrt(rows)`), tuned at query time with
  `SET ivfflat.probes`. Only pick IVFFlat when build time / memory of HNSW is the constraint.
- Build the HNSW index **after** a bulk load (or raise `maintenance_work_mem`) — building on an
  empty table then inserting millions is slow.

## Recipe B — Qdrant

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")  # or QdrantClient(":memory:") to try it

client.create_collection(
    collection_name="chunks",
    vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
    hnsw_config=models.HnswConfigDiff(m=16, ef_construct=100),
)

# CRITICAL for fast filtering: create payload indexes BEFORE ingesting.
# Qdrant only builds the filter-aware graph edges once these exist.
client.create_payload_index("chunks", "category", models.PayloadSchemaType.KEYWORD)
client.create_payload_index("chunks", "doc_id",   models.PayloadSchemaType.KEYWORD)
```

Query with a filter and per-query `ef`:

```python
hits = client.query_points(
    collection_name="chunks",
    query=q_vector,
    query_filter=models.Filter(must=[
        models.FieldCondition(key="category", match=models.MatchValue(value="faq"))
    ]),
    search_params=models.SearchParams(hnsw_ef=128),  # recall/speed knob at query time
    limit=10,
).points
```

Notes:
- Payload indexes **before** data — adding them after means re-indexing to get the speedup.
- Doesn't fit in RAM? Set `on_disk=True` on `HnswConfigDiff`/`VectorParams`, or enable scalar
  quantization (`quantization_config=models.ScalarQuantization(...)`) to shrink ~4×.

## Recipe C — Chroma (prototype)

```python
import chromadb
client = chromadb.PersistentClient(path="./chroma")   # on-disk; not just in-memory

col = client.get_or_create_collection(
    name="chunks",
    metadata={"hnsw:space": "cosine", "hnsw:M": 16, "hnsw:construction_ef": 100},
)
col.add(ids=ids, embeddings=vecs, documents=texts,
        metadatas=[{"category": "faq", "doc_id": d} for d in doc_ids])

res = col.query(query_embeddings=[q_vector], n_results=10,
                where={"category": "faq"})   # metadata filter
```

Chroma is fine to ~1M vectors on one box. Past that, or when you need real concurrency /
sharding, migrate (below). Set `hnsw:search_ef` in metadata to trade recall vs speed.

## Recipe D — LanceDB (embedded, disk-scale)

```python
import lancedb
db = lancedb.connect("./lance")
tbl = db.create_table("chunks", data=rows)   # rows: dicts with a "vector" list + metadata

# IVF_PQ defaults: num_partitions ≈ rows/4096, num_sub_vectors ≈ dim/8
tbl.create_index(metric="cosine", num_partitions=256, num_sub_vectors=96)
tbl.create_scalar_index("category")          # BTREE scalar index for fast metadata filtering

res = (tbl.search(q_vector).where("category = 'faq'")
          .nprobes(20).refine_factor(10).limit(10).to_list())
```

Notes: LanceDB partitions by IVF then searches within partitions (HNSW is a sub-index, not a
top-level type). Tune recall with **`nprobes`** (more partitions scanned) and **`refine_factor`**
(re-rank with full vectors). It scales past RAM because data lives in the Lance columnar files.

## Verify

- **Recall spot-check:** brute-force the exact top-10 for ~20 sample queries (no index / full
  scan) and compare to indexed results — aim for ≥ 0.95 overlap. If low, raise `ef_search` /
  `hnsw_ef` / `nprobes` first, then `ef_construction` / `m` (needs a rebuild).
- **Filter is actually pushed down:** pgvector `EXPLAIN ANALYZE` should use the metadata index;
  Qdrant/LanceDB should be fast *with* the filter (slow-with-filter ⇒ missing payload/scalar index).
- **Latency under load, not single-shot.** Measure p95 at your real concurrency and top-k.
- **Dim + metric match the model.** A cosine model in an L2 index looks "working" but ranks wrong.

## Pitfalls

- **Metric mismatch** — cosine model in an L2/inner-product index. Most common silent failure.
- **Filtering without an index** — the killer for Qdrant/LanceDB filtered search; create payload /
  scalar indexes *before* ingesting. In pgvector, a missing B-tree forces a full scan.
- **Over-densifying HNSW** — `m` above ~24–32 mostly buys build time and RAM, not recall; tune
  `ef_search` at query time before touching `m`.
- **>2000 dims in pgvector `vector`** — the index errors out; use `halfvec` + `halfvec_cosine_ops`.
- **IVFFlat/IVF_PQ built on too little data** — needs representative rows to train partitions;
  build after loading, and rebuild after big inserts to avoid drifting centroids.
- **Building HNSW then bulk-inserting** — far slower than load-then-index; bump
  `maintenance_work_mem` (pgvector) or index after ingest.
- **Staying on Chroma too long** — migrate around ~1M vectors or when you need concurrency,
  auth, sharding, or hybrid/quantization: re-embed is unnecessary, just stream `(id, vector,
  payload)` into a Qdrant collection or pgvector table and rebuild the index.

## Sources

pgvector (`github.com/pgvector/pgvector`), Qdrant docs (`qdrant.tech/documentation`),
Chroma docs (`docs.trychroma.com`), LanceDB docs (`docs.lancedb.com`). Verified 2026-07-09.
