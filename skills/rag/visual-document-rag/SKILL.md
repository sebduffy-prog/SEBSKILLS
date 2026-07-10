---
name: visual-document-rag
category: rag
description: >
  Retrieve over PDF/deck/scan PAGES AS IMAGES using ColPali-family late-interaction
  multimodal models (ColQwen2.5, ColPali, ColSmol) — no OCR, no chunking, no layout
  parsing. Each page becomes a multi-vector (one embedding per patch/token) scored by
  MaxSim, so charts, tables, logos, screenshots and dense-layout decks stay searchable.
  Use when text extraction mangles a document, when the answer lives in a figure or table,
  or when you ask "ColPali", "ColQwen", "ColQwen2.5", "byaldi", "visual RAG", "screenshot
  RAG", "search PDFs by page image", "late interaction", "MaxSim", "ViDoRe", "multimodal
  retrieval", "RAG over slides/decks/scanned docs".
when_to_use:
  - "OCR/text extraction garbles the source (scanned reports, image-only PDFs, dense PowerPoint decks) so text RAG retrieves nothing useful"
  - "The answer lives in a chart, table, diagram, logo, or screenshot that a text pipeline flattens or drops"
  - "You want to skip the whole parse→layout→chunk→embed pipeline and index pages directly as images"
  - "You ask for ColPali / ColQwen2.5 / byaldi / late-interaction / MaxSim visual retrieval over PDFs or slides"
  - "Building a visual-first RAG stage that feeds top-k page images into a vision LLM (GPT-4o, Claude, Qwen2-VL) for the answer"
  - "Benchmarking a visual retriever against ViDoRe before committing to it"
when_not_to_use:
  - "Source is clean machine-readable text (Markdown, HTML, code) — use rag-chunking-contextual + vector-store-setup instead"
  - "You already have text chunks and need to fix recall/precision — use hybrid-search-reranking"
  - "You need entity/relationship traversal over the corpus — use graphrag-builder"
  - "Measuring retrieval quality (recall@k, nDCG) once built — use llm-rag-eval-harness"
  - "Just splitting a very long text document into passages — use long-doc-chunking"
keywords: [colpali, colqwen, colqwen2.5, byaldi, visual rag, multimodal retrieval, late interaction, maxsim, vidore, screenshot rag, pdf page image, document retrieval, colsmol, multi-vector, vision language model, pdf2image, qdrant multivector, ocr-free]
similar_to: [rag-chunking-contextual, hybrid-search-reranking, graphrag-builder, llm-rag-eval-harness, vector-store-setup, retrieval-as-context, long-doc-chunking, agentic-rag-pipeline]
inputs_needed:
  - Source documents as PDFs or page images (decks, scanned reports, screenshots); poppler installed if converting PDFs
  - A CUDA GPU (or Apple MPS) — ColPali models are ~2-7B params and slow to embed on CPU; Python >=3.10 for colpali-engine
  - Choice of path — byaldi (fastest to a working demo, in-memory index) or colpali-engine + a multi-vector store (Qdrant) for production
  - A vision LLM for the generation step (optional) if you want end-to-end answers, not just retrieved page images
produces: An OCR-free page-image retriever (byaldi index or colpali-engine + Qdrant multivector collection) returning top-k page images ranked by MaxSim, ready to feed a vision LLM
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Visual Document RAG (ColPali / ColQwen late interaction)

Text RAG assumes the document *is* text. Decks, scanned reports, and figure-heavy PDFs
break that assumption — OCR mangles multi-column layouts, chunkers destroy tables, and the
answer is often a **chart** with no extractable words at all. ColPali-family models skip
parsing entirely: render each page to an image, embed it as a grid of patch vectors with a
vision-language model, and score queries against pages with **late interaction (MaxSim)** —
the same ColBERT trick, but the "tokens" are image patches. State of the art on **ViDoRe**,
and it just works on slides and scans that text pipelines can't touch.

## When to use

Reach for this the moment text extraction is the bottleneck: the source is scanned or
image-only, the answer lives in a figure/table/screenshot, or you're tired of tuning a
parse→OCR→chunk pipeline that still misses. If your corpus is clean text, this is overkill —
use `rag-chunking-contextual` + `vector-store-setup`.

## Prerequisites

- **Python >= 3.10** (colpali-engine requires it; this macOS box ships 3.9 — use a GPU box,
  Colab, or a `uv`/conda 3.11 env). A CUDA GPU is strongly recommended; MPS works but is slow.
- `pip install byaldi` (easy path) **or** `pip install colpali-engine>=0.3.10` (production path).
- **PDF→image** needs poppler: `apt-get install poppler-utils` (Linux) — then `pip install pdf2image pillow`. byaldi handles PDFs internally if poppler is present.
- Model weights are gated-free on HF. First run downloads ~2-7 GB. `pip install huggingface_hub`.

**Model picker** (higher ViDoRe = better; bigger = slower/more VRAM):

| Model | HF id | ViDoRe v1 | Notes |
|-------|-------|-----------|-------|
| ColQwen2.5-v0.2 | `vidore/colqwen2.5-v0.2` | ~89.4 | Current SOTA general pick |
| ColQwen2-v1.0 | `vidore/colqwen2-v1.0` | ~89.3 | Well-supported in byaldi |
| ColPali-v1.3 | `vidore/colpali-v1.3` | ~84.8 | PaliGemma base, smaller |
| ColSmol-256M/500M | `vidore/colSmol-256M` | lower | Runs on CPU / edge |

## Recipe A — byaldi (fastest to a working retriever)

byaldi (from Answer.AI) wraps colpali-engine with a familiar `index`/`search` API. In-memory
index, great for a demo or a corpus of a few hundred pages.

```python
from byaldi import RAGMultiModalModel

# Load. Pass device="cuda" | "mps" | "cpu"; defaults to best available.
RAG = RAGMultiModalModel.from_pretrained("vidore/colqwen2-v1.0", device="cuda")

# Index a PDF, an image, or a whole directory. store_collection_with_index=True
# keeps the base64 page image in the index so search() can return it directly.
RAG.index(
    input_path="decks/",
    index_name="vccp_decks",
    store_collection_with_index=True,
    overwrite=True,
)

# Query in natural language — no keywords needed.
results = RAG.search("Q3 media spend split by channel", k=3)
for r in results:
    print(r["doc_id"], r["page_num"], round(r["score"], 3))
    # r["base64"] is the page image (present only if store_collection_with_index=True)

# Grow the index later without rebuilding:
RAG.add_to_index("decks/new_pitch.pdf", store_collection_with_index=True)
```

Result dicts: `doc_id` (0-indexed), `page_num` (1-indexed), `score` (MaxSim float),
`metadata`, and `base64` when stored. See `scripts/byaldi_index_search.py` for a runnable CLI.

## Recipe B — colpali-engine direct (control the embeddings)

Use this when you want the raw multi-vectors — to store them in Qdrant, quantize, or rerank.

```python
import torch
from PIL import Image
from colpali_engine.models import ColQwen2_5, ColQwen2_5_Processor

name = "vidore/colqwen2.5-v0.2"
model = ColQwen2_5.from_pretrained(
    name, torch_dtype=torch.bfloat16, device_map="cuda:0"
).eval()
processor = ColQwen2_5_Processor.from_pretrained(name)

images = [Image.open("page_001.png").convert("RGB")]
queries = ["What is the year-over-year revenue change?"]

with torch.no_grad():
    img_emb = model(**processor.process_images(images).to(model.device))    # [n, patches, dim]
    q_emb   = model(**processor.process_queries(queries).to(model.device))  # [n, tokens,  dim]

# MaxSim scoring — for each query token take the best-matching page patch, then sum.
scores = processor.score_multi_vector(q_emb, img_emb)  # [n_queries, n_images]
print(scores)
```

For **ColPali** use `ColPali` / `ColPaliProcessor`; for **ColQwen2** use `ColQwen2` /
`ColQwen2Processor`. The processor exposes `score_multi_vector` for MaxSim on every variant.

### Storing in Qdrant (production, multi-vector native)

Qdrant supports late-interaction natively via `MultiVectorConfig` — store the per-patch
matrix per page and let Qdrant do MaxSim server-side:

```python
from qdrant_client import QdrantClient, models

client = QdrantClient(url="http://localhost:6333")
client.create_collection(
    "pages",
    vectors_config=models.VectorParams(
        size=128,  # ColQwen2.5 per-vector dim
        distance=models.Distance.COSINE,
        multivector_config=models.MultiVectorConfig(
            comparator=models.MultiVectorComparator.MAX_SIM
        ),
    ),
)
# Upsert one point per page; vector = list-of-lists (patch embeddings, cast to float32).
client.upsert("pages", [models.PointStruct(
    id=0, vector=img_emb[0].cpu().float().tolist(),
    payload={"pdf": "deck.pdf", "page": 1},
)])
hits = client.query_points("pages", query=q_emb[0].cpu().float().tolist(), limit=3).points
```

Patch matrices are large (~1030 vectors × 128 dims per page). For big corpora, enable
scalar/binary quantization and/or a two-stage mean-pooled prefetch — see Qdrant's ColPali docs.

## The generation step

Retrieval returns **page images**, not text. Feed the top-k images straight into a vision
LLM (Claude, GPT-4o, Qwen2-VL) with the question — that is the whole point: the model reads
the chart/table itself. Pair this skill with `retrieval-as-context` for the prompt assembly.

## Verify

```bash
python3 -m py_compile scripts/byaldi_index_search.py   # syntax check (no GPU needed)
```

On a GPU box, index a 5-page PDF and confirm a query about a **figure** (not body text)
returns the right `page_num` — that is what proves the visual path beats OCR. Sanity checks:

- Scores are unnormalized MaxSim floats; compare **within** a query's result set, not across queries.
- Ask a chart-only question and a text-only question; both should land the correct page. If the
  chart one fails, your PDF likely rasterized at too low a DPI (render at >=150 DPI).
- Benchmark against `vidore/vidore-benchmark` before trusting a model on your domain.

## Pitfalls

- **Python 3.9 won't work.** colpali-engine needs >=3.10. This Mac is 3.9 — run on Colab/GPU/`uv` env.
- **CPU is painfully slow.** Embedding is a full VLM forward pass per page. Batch on GPU, or use ColSmol for CPU/edge.
- **Storage blows up.** Multi-vector = ~1000 vectors/page. A 10k-page corpus is hundreds of millions of floats — quantize, or use byaldi only for small sets.
- **`store_collection_with_index=False`** means `search()` returns no `base64` — you must map `doc_id`/`page_num` back to your own page images yourself.
- **Low-DPI rasterization loses fine print.** Render PDF pages at 150-200 DPI; tiny table text needs the resolution.
- **Model/processor class must match the checkpoint** — `ColQwen2_5` for colqwen2.5, `ColQwen2` for colqwen2, `ColPali` for colpali. Mismatches raise on load.
- **Don't normalize or fuse MaxSim scores like cosine.** They are sums over token maxima; RRF/rank-fusion is fine, min-max rescaling across queries is not.
- **Not a replacement for text RAG on clean text** — for machine-readable docs it costs far more for no gain.
