---
name: lancedb-multimodal-store
category: rag
description: >
  Build an embedded LanceDB/Lance multimodal store that keeps vectors, raw media bytes
  (images, audio, video frames, PDFs) and metadata together in ONE columnar lakehouse —
  no server, no separate blob bucket. Reach for this when a RAG index must return the
  actual asset, not just a text chunk: image search, product catalogues, ad-creative
  libraries, screenshot/thumbnail retrieval, or any store mixing vector + full-text +
  SQL filters. Covers create_table with a pydantic schema, auto-embedding via the
  embeddings registry, blob columns for large media, ANN + FTS indexes, and hybrid search.
when_to_use:
  - You need vectors, raw media bytes, and metadata co-located in one embedded store with zero infra
  - Retrieval must return the actual image/audio/video/PDF asset, not just a text snippet
  - You want vector search, full-text search, and SQL-style metadata filters over the same table
  - Building an ad-creative, product, or screenshot library where each row carries a real file
  - You want auto-embedding on insert/search via the LanceDB embeddings registry (no manual encode step)
  - You need cheap local prototyping that later scales to S3/GCS or LanceDB Cloud unchanged
when_not_to_use:
  - Pure text-chunk RAG with no media payload — use vector-store-setup instead
  - You mainly need reranked keyword+vector fusion tuning — use hybrid-search-reranking
  - Parsing/OCR of PDFs into page images for retrieval — use visual-document-rag first, store here after
  - You need entity/relationship graph retrieval — use graphrag-builder
keywords:
  - lancedb
  - lance
  - multimodal
  - vector-store
  - embeddings
  - blob
  - hybrid-search
  - full-text-search
  - fts
  - ann-index
  - pyarrow
  - image-search
  - lakehouse
  - rag
  - embedded-database
similar_to:
  - vector-store-setup
  - hybrid-search-reranking
  - visual-document-rag
  - agentic-rag-pipeline
inputs_needed: A folder of media (images/audio/etc.) with optional captions or metadata; Python 3.9+; optional embedding model (local sentence-transformers, or an API key for OpenAI/Voyage multimodal).
produces: A local Lance dataset directory (.lance) holding vectors + raw media + metadata, with FTS and ANN indexes, queryable by vector, full-text, and hybrid search from Python.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# LanceDB Multimodal Store

Keep the **embedding, the raw file, and the metadata in the same row** of one embedded
columnar table. LanceDB is built on the Lance format, so binary media lives on disk next
to the vectors — search returns the asset itself, and there is no server or object bucket
to run. This skill grounds every call against the real `lancedb` Python API (verified
against lancedb 0.35, `create_fts_index` native/Tantivy-free, `query_type="hybrid"`).

## When to use

Text-centric RAG stores throw away the source file. Use this when retrieval must hand back
the **actual creative** — an image, an audio clip, a video thumbnail, a rendered PDF page —
alongside its metadata, and you want vector + keyword + SQL filters over one table without
standing up Qdrant/pgvector + an S3 bucket + a metadata DB.

## Prerequisites

- **Python 3.9+**. Install (macOS, no brew needed):
  ```bash
  pip install "lancedb>=0.13" pyarrow pandas
  pip install "sentence-transformers"          # local embeddings, no API key
  # optional multimodal / hosted embeddings:
  # pip install "open-clip-torch"  or  set OPENAI_API_KEY / VOYAGE_API_KEY
  ```
- **No server, no keys** for the local path — `lancedb.connect("./data")` writes a
  directory. The *same code* connects to S3/GCS (`connect("s3://bucket/db")`) or LanceDB
  Cloud (`connect("db://...", api_key=...)`).
- Local sentence-transformers models download once (~90 MB for `all-MiniLM-L6-v2`).

## Recipe 1 — One-shot builder (folder of images → searchable store)

`scripts/build_store.py` ingests a folder into a table with a blob-ish `image` column,
an FTS-indexed `caption`, and an auto-embedded `vector`, then runs all three searches:

```bash
python3 scripts/build_store.py ./images ./lance_data assets
```

It uses `LanceModel` + the embeddings registry so captions are embedded automatically on
both write and query — you never call `.encode()` yourself.

## Recipe 2 — Auto-embedding schema (the core pattern)

```python
import lancedb
from lancedb.embeddings import get_registry
from lancedb.pydantic import LanceModel, Vector

embedder = get_registry().get("sentence-transformers").create(
    name="all-MiniLM-L6-v2", device="cpu"
)

class Asset(LanceModel):
    id: str
    caption: str = embedder.SourceField()          # text that gets embedded
    vector: Vector(embedder.ndims()) = embedder.VectorField()  # 384-dim here
    image: bytes                                    # raw media in the row
    campaign: str                                   # arbitrary metadata

db = lancedb.connect("./lance_data")
tbl = db.create_table("assets", schema=Asset, mode="overwrite")
tbl.add([
    {"id": "a1", "caption": "golden retriever on a beach",
     "image": open("dog.jpg", "rb").read(), "campaign": "summer26"},
])

# Query strings are embedded automatically because of SourceField/VectorField.
tbl.search("a happy dog by the sea").limit(5).to_pandas()
```

Prefer a **pydantic schema over dict inference** — it pins vector dimensions and column
types so ingest can't silently drift.

## Recipe 3 — Indexes, then vector / FTS / hybrid search

```python
tbl.create_fts_index("caption", replace=True)          # native FTS (no Tantivy dep)
# ANN index trains on the data — needs a few hundred+ rows to be worthwhile:
if tbl.count_rows() >= 256:
    tbl.create_index(metric="cosine", vector_column_name="vector")

tbl.search("dog", query_type="fts").limit(5).to_pandas()       # keyword
tbl.search("a happy dog").limit(5).to_pandas()                 # vector (default)

from lancedb.rerankers import RRFReranker
(tbl.search("a happy dog", query_type="hybrid")
    .rerank(RRFReranker())
    .limit(5)
    .to_pandas())                                              # fused vector+FTS
```

Combine with metadata: `.where("campaign = 'summer26'")` pushes a SQL predicate into the
scan, and `.select(["id", "caption"])` avoids dragging blob bytes back when you only need
metadata.

## Recipe 4 — Large media as blob columns (lazy, out-of-line)

Inlining big files bloats every scan. Declare the media column as a **blob** so bytes are
stored out-of-line and loaded only when asked. Build the table from a pyarrow schema where
the binary field carries the `lance-encoding:blob` metadata:

```python
import pyarrow as pa

media_field = pa.field(
    "media", pa.large_binary(), metadata={"lance-encoding:blob": "true"}
)
schema = pa.schema([
    pa.field("id", pa.string()),
    pa.field("vector", pa.list_(pa.float32(), 384)),
    media_field,
])
tbl = db.create_table("big_assets", schema=schema)

# Retrieve blobs lazily via the underlying Lance dataset (files, not raw bytes):
ds = tbl.to_lance()
blobs = ds.take_blobs([0, 1], "media")     # list of file-like BlobFile objects
data = blobs[0].readall()
```

Rule of thumb: **inline `bytes` under ~128 KB, blob-encode above it**; vectors + metadata
stay small so vector/FTS/hybrid scans never touch the media bytes.

## Verify

```bash
python3 -c "import ast; ast.parse(open('scripts/build_store.py').read()); print('syntax OK')"
python3 scripts/build_store.py ./images ./lance_data assets   # prints row count + 3 searches
python3 -c "import lancedb; d=lancedb.connect('./lance_data'); \
t=d.open_table('assets'); print(t.count_rows(), t.schema)"
```
Success = the store prints a non-zero row count and returns rows for vector, fts, and
hybrid queries; the on-disk `./lance_data/assets.lance` directory exists.

## Pitfalls

- **FTS is async to build.** `create_fts_index` returns immediately; on a fresh tiny table
  query right after — or pass `wait_timeout` — before asserting FTS hits.
- **ANN index needs data to train.** On <256 rows skip `create_index`; brute-force vector
  scan is exact and fast at that size. Creating it too early errors or wastes effort.
- **`query_type="hybrid"` requires BOTH** a vector column and an FTS index on the text
  column, or it silently degrades. Create the FTS index first.
- **Dimension mismatch** between the query embedder and the stored `Vector(n)` throws at
  search time — always derive `Vector(embedder.ndims())`, never hardcode.
- **Don't select blob columns you don't need.** `.select([...])` metadata-only keeps scans
  cheap; pulling `image`/`media` on every hybrid search re-materializes megabytes.
- **`mode="overwrite"` / `drop_table` are destructive.** Guard with `table_names()` in
  pipelines; there is no undo on a local Lance dir.
- **Pin the version.** LanceDB moves fast; `create_fts_index` defaults to native FTS now
  (Tantivy is opt-in via `use_tantivy=True`). Test against `pip freeze | grep lancedb`.
