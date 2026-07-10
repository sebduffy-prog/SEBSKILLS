---
name: graphrag-builder
category: rag
description: >
  Build and query a knowledge-graph RAG system so you can answer multi-hop and global-summary
  questions that plain vector RAG cannot ("what are the top themes across all docs", "how does X
  connect to Y three hops away"). Extract an entity/relationship graph + community summaries from a
  corpus using Microsoft GraphRAG (CLI), LightRAG, or nano-graphrag, then run global/local/hybrid/drift
  queries. Use when someone says graph RAG, GraphRAG, knowledge graph RAG, LightRAG, community summaries,
  global search, multi-hop retrieval, or "vector search keeps missing the big picture".
when_to_use:
  - "User asks a corpus-wide / thematic question ('what are the main themes', 'summarise everything') that needs whole-corpus reasoning, not top-k chunks"
  - "Questions require multi-hop reasoning across entities ('how is A connected to C?') that vector similarity misses"
  - "User explicitly wants GraphRAG, LightRAG, nano-graphrag, a knowledge graph over their docs, or community/global summaries"
  - "An existing vector RAG returns locally-relevant chunks but fails at synthesis or connecting facts across documents"
  - "User wants both local (entity-precise) and global (theme-level) retrieval from one index"
when_not_to_use:
  - "Plain semantic retrieval over chunks is enough — use vector-store-setup + rag-chunking-contextual"
  - "You just need better ranking of retrieved chunks — use hybrid-search-reranking"
  - "You need a tool-calling agent that decides when/what to retrieve — use agentic-rag-pipeline"
  - "You only need to measure an existing RAG's accuracy — use llm-rag-eval-harness"
  - "Chunking a single very long document for a vector index — use long-doc-chunking"
keywords: [graphrag, graph rag, knowledge graph rag, lightrag, nano-graphrag, microsoft graphrag, community summaries, global search, local search, multi-hop, entity extraction, drift search, leiden, hybrid retrieval, knowledge graph, graph index]
similar_to: [rag-chunking-contextual, hybrid-search-reranking, agentic-rag-pipeline, retrieval-as-context, vector-store-setup]
inputs_needed:
  - "The corpus (plain .txt/.md files or a folder) and roughly how large it is — graph indexing is LLM-heavy and cost scales with corpus size"
  - "Which engine: Microsoft GraphRAG (batteries-included CLI), LightRAG (fast, incremental, Python), or nano-graphrag (~1100 LOC, hackable)"
  - "An LLM + embedding provider and key (OpenAI by default; local via Ollama supported) plus a cost ceiling"
produces: A persisted knowledge-graph index (entities, relationships, community reports) plus working global/local/hybrid query calls returning cited answers.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# GraphRAG Builder

Graph RAG extracts an **entity–relationship graph** from your corpus, clusters it into
**communities**, and pre-generates **community summaries**. That unlocks two retrieval modes
plain vector RAG can't do:

- **Global search** — answer whole-corpus questions ("top themes?") by map-reducing over
  community summaries instead of top-k chunks.
- **Local/hybrid search** — answer entity-specific questions by walking the graph neighbourhood
  of matched entities, not just cosine-nearest chunks.

Pick an engine by need. **Microsoft GraphRAG** = most complete, CLI-driven, expensive to index.
**LightRAG** = fast, incremental inserts, dual-level Python API. **nano-graphrag** = ~1100 LOC,
easiest to read and modify. All three ground against their real docs below.

## When to use

Reach for graph RAG when the failure mode of your current RAG is *synthesis* or *connection*:
"summarise across all docs", "how does X relate to Y", corpus-wide themes. If top-k chunks already
answer the question, stay on a vector store — graph indexing costs many LLM calls up front.

## Prerequisites

- Python 3.10–3.12.
- An LLM + embedding provider. OpenAI is the default path; set `OPENAI_API_KEY`. Local models via
  Ollama or an OpenAI-compatible endpoint work for LightRAG / nano-graphrag.
- **Budget awareness**: indexing calls the LLM once per chunk (entity extraction) plus once per
  community (summaries). A book-sized corpus is cheap; thousands of docs is not. Start on a small
  sample and use a mini model for extraction.

```bash
export OPENAI_API_KEY="sk-..."
```

## Recipe A — Microsoft GraphRAG (CLI, batteries included)

Best when you want a turnkey pipeline and don't need to touch Python.

```bash
python -m pip install graphrag

# 1. Scaffold a project (creates ./ragtest with settings.yaml, .env, prompts/)
graphrag init --root ./ragtest

# 2. Add corpus: drop .txt files into the input dir
mkdir -p ./ragtest/input
cp mydocs/*.txt ./ragtest/input/

# 3. Set your key in ./ragtest/.env
#    GRAPHRAG_API_KEY=<your OpenAI or Azure key>
#    (tune model + chunk size in ./ragtest/settings.yaml)

# 4. Build the graph index (entity extraction + community reports -> ./ragtest/output/*.parquet)
graphrag index --root ./ragtest

# 5. Query. --method is one of: global | local | drift | basic (default: global)
graphrag query --root ./ragtest --method global \
  --query "What are the top themes across these documents?"

graphrag query --root ./ragtest --method local \
  --query "Who is Scrooge and what are his key relationships?"
```

Modes: **global** map-reduces over community reports (corpus-wide questions); **local** walks the
neighbourhood of matched entities (specific facts); **drift** blends both with follow-up expansion;
**basic** is vanilla vector RAG for comparison. Cheaper indexing: `graphrag index --method fast`.

## Recipe B — LightRAG (Python, fast, incremental)

Best for programmatic use, incremental `ainsert` (no full re-index), and a dual-level API.

```bash
pip install "lightrag-hku[api]"
```

```python
import asyncio
from lightrag import LightRAG, QueryParam
from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
from lightrag.kg.shared_storage import initialize_pipeline_status

async def main():
    rag = LightRAG(
        working_dir="./lightrag_store",
        llm_model_func=gpt_4o_mini_complete,   # extraction + generation
        embedding_func=openai_embed,           # entity/chunk embeddings
    )
    # Both init calls are REQUIRED before insert/query in current LightRAG:
    await rag.initialize_storages()
    await initialize_pipeline_status()

    with open("./book.txt", encoding="utf-8") as f:
        await rag.ainsert(f.read())            # incremental; call again to add more

    # modes: naive | local | global | hybrid | mix (mix = graph + vector, best default)
    print(await rag.aquery(
        "What are the top themes in this story?",
        param=QueryParam(mode="global"),
    ))
    print(await rag.aquery(
        "How is character A connected to character B?",
        param=QueryParam(mode="hybrid"),
    ))
    await rag.finalize_storages()

asyncio.run(main())
```

LightRAG modes: **naive** (vector only), **local** (entity neighbourhood), **global**
(relationship/theme level), **hybrid** (local+global), **mix** (graph + vector — usually the
strongest). For local LLMs, swap the funcs for `lightrag.llm.ollama` equivalents.

## Recipe C — nano-graphrag (hackable, ~1100 LOC)

Best when you want to read/modify the whole pipeline (custom chunking, storage, prompts).

```bash
pip install nano-graphrag
```

```python
from nano_graphrag import GraphRAG, QueryParam

graph = GraphRAG(working_dir="./nano_store")   # reads OPENAI_API_KEY from env

with open("./book.txt") as f:
    graph.insert(f.read())

# global search (default): map-reduce over community reports
print(graph.query("What are the top themes in this story?"))

# local search: entity-neighbourhood retrieval
print(graph.query(
    "What does the text say about Scrooge?",
    param=QueryParam(mode="local"),
))
```

Everything (entity extraction prompt, Leiden clustering, storage backends) is swappable via
constructor args — see the repo's `using_custom_chunking_method` and local-LLM examples.

## Verify

- **Index produced a graph, not just chunks.** GraphRAG: confirm `./ragtest/output/` contains
  `entities`, `relationships`, and `community_reports` parquet files. LightRAG/nano: the
  `working_dir` should hold a graph file (e.g. `graph_chunk_entity_relation.graphml`) plus vector
  stores — not only chunk KV.
- **Global vs local actually differ.** Ask one corpus-wide question in `global`/`mix` and one
  entity-specific question in `local`. If both modes return near-identical answers, extraction
  likely under-populated the graph (too-large chunks or a weak extraction model) — shrink chunk
  size and re-index.
- **Answers cite sources.** GraphRAG responses reference community/report ids; sanity-check a
  couple of claims against the source text before trusting synthesis.
- **A/B against vector RAG.** Run the same corpus-wide question through a plain vector store; graph
  RAG should win on synthesis/connection questions. If it doesn't, the corpus may not need a graph.

## Pitfalls

- **Indexing cost explodes with corpus size.** Entity extraction is one LLM call per chunk. Always
  pilot on a small sample, use a `mini`/`flash` model for extraction, and cache. GraphRAG's own docs
  warn it "can consume a lot of LLM resources."
- **Garbage graph from bad chunking.** Too-large chunks -> sparse, generic entities -> useless
  communities. Keep extraction chunks modest and domain-tune the extraction prompt (all three
  engines expose it).
- **Global search is not for lookups.** Using `global` for "what is entity X's phone number" wastes
  a full map-reduce and often answers worse than `local`. Route point-lookups to local/hybrid.
- **LightRAG init order.** Forgetting `initialize_storages()` **and** `initialize_pipeline_status()`
  before insert/query is the #1 LightRAG error — both are required.
- **Version drift.** These libraries move fast; APIs (esp. LightRAG imports and GraphRAG CLI flags)
  change between releases. If a call fails, check the installed version's README/examples rather than
  guessing — pin versions in production.
- **Not a drop-in for streaming/real-time.** Graph rebuild is batchy. LightRAG's incremental
  `ainsert` is the friendliest for updates; GraphRAG needs `--method *-update` or a re-index.
