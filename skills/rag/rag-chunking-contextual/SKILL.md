---
name: rag-chunking-contextual
category: rag
description: >
  Choose and implement the right RAG chunking + embedding strategy — fixed-token, recursive,
  semantic, hierarchical/parent-child, and late chunking — then bolt on Anthropic Contextual
  Retrieval so every chunk carries a self-contained situating blurb before it is embedded and
  BM25-indexed. Use when chunks retrieve badly, lose context, split mid-thought, or when you ask
  "how should I chunk my documents", "what chunk size", "why is my RAG missing obvious answers",
  "contextual retrieval", "late chunking", or "add context to chunks before embedding".
when_to_use:
  - "Building a RAG ingest pipeline and deciding how to split documents into chunks"
  - "Retrieval misses answers that are obviously in the corpus, or returns chunks that read as orphaned fragments"
  - "You want to implement Anthropic's Contextual Retrieval (context-prepended chunks) to cut retrieval failures"
  - "Long documents where a chunk references 'the company', 'this method', 'it' without the antecedent"
  - "Deciding between fixed / recursive / semantic / hierarchical / late chunking for a specific corpus"
  - "Picking chunk size + overlap and an embedding model for a new vector store"
when_not_to_use:
  - "You already have good chunks and only need lexical+vector fusion or a reranker — use hybrid-search-reranking"
  - "Entity/relationship-graph retrieval over the corpus — use graphrag-builder"
  - "Measuring retrieval quality (recall@k, nDCG, faithfulness) — use llm-rag-eval-harness"
  - "Multi-step retrieve-reason-retrieve agent loops — use agentic-rag-pipeline"
  - "Provisioning the vector DB itself (collections, indexes, upserts) — use vector-store-setup"
  - "Splitting one huge document for summarization rather than retrieval — use long-doc-chunking"
keywords: [chunking, contextual retrieval, late chunking, semantic chunking, recursive splitter, chunk size, overlap, parent-child, hierarchical chunking, embeddings, jina, anthropic cookbook, bm25, prompt caching, rag ingest, chunk context, contextual embeddings]
similar_to: [hybrid-search-reranking, long-doc-chunking, vector-store-setup, graphrag-builder, agentic-rag-pipeline]
inputs_needed:
  - "Corpus type + typical doc length (support tickets vs 200-page PDFs vs code)"
  - "Embedding model / max context window (decides if late chunking is even possible)"
  - "Whether an ANTHROPIC_API_KEY is available for Contextual Retrieval, and budget tolerance"
  - "Downstream retriever (dense-only, hybrid, reranked) so chunk shape matches it"
produces: A chosen chunking strategy plus runnable ingest code that emits context-enriched chunks ready to embed and BM25-index
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# RAG Chunking + Contextual Retrieval

Pick a chunking strategy that fits the corpus, then make each chunk **self-contained** before it is
embedded. Two independent levers that stack:

1. **Chunking strategy** — how you cut the document (fixed / recursive / semantic / hierarchical / late).
2. **Contextual enrichment** — prepend a short situating blurb to each chunk so it stops being an orphan
   fragment. Anthropic's Contextual Retrieval cut retrieval failures **35%** (contextual embeddings),
   **49%** (+ contextual BM25), and **67%** (+ reranking).

## When to use

Reach for this at ingest-design time, or when retrieval is silently failing: the answer is in the corpus
but the chunk that holds it says "it dropped 3%" with no idea what "it" is. That is a chunking/context
problem, not a retriever problem.

## Prerequisites

- **Contextual Retrieval:** `pip install anthropic` and an `ANTHROPIC_API_KEY`. Uses Claude Haiku +
  prompt caching → ~**$1.02 per million document tokens** (caching makes it viable; without it, cost
  explodes because you'd resend the whole doc per chunk).
- **Late chunking:** `pip install "transformers>=4.40" torch` and a **mean-pooling long-context** embed
  model (e.g. `jinaai/jina-embeddings-v2-base-en`, 8192 tokens). Or the hosted Jina API with
  `late_chunking=True` — no local model. Late chunking ONLY works on mean-pooled models; it is a no-op
  on CLS-pooled ones.
- **Semantic chunking:** an embedding model to score adjacent-sentence similarity (any dense model).
- Fixed/recursive need nothing beyond a tokenizer.

## Choosing a strategy

| Strategy | Cut on | Best for | Cost | Notes |
|---|---|---|---|---|
| **Fixed-token** | N tokens + overlap | uniform text, quick baseline | ~0 | dumb but robust; start here |
| **Recursive** | paragraph→sentence→word boundaries | prose, markdown, mixed docs | ~0 | default for most corpora; respects structure |
| **Semantic** | embedding-similarity drop between sentences | topic-shifting docs, transcripts | 1 embed pass | variable-size chunks; needs a breakpoint threshold |
| **Hierarchical (parent-child)** | small children indexed, large parent returned | precise match + rich context | ~0 | embed small, return big; great with rerankers |
| **Late chunking** | chunk AFTER full-doc embedding | keeps global context in every chunk vector | 1 long-ctx pass | fixes pronoun/antecedent loss without an LLM |

Defaults that rarely go wrong: **recursive, ~250–500 tokens, ~10–15% overlap**, then add **Contextual
Retrieval** on top. Only reach for semantic/late chunking when you can measure that they beat that
baseline (use `llm-rag-eval-harness`).

## Recipe 1 — Recursive baseline (start here)

```python
# pip install langchain-text-splitters tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=400,        # tokens, not chars
    chunk_overlap=60,      # ~15%
    separators=["\n\n", "\n", ". ", " ", ""],  # try coarse boundaries first
)
chunks = splitter.split_text(document)   # list[str]
```

No LangChain? A dependency-free token splitter:

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
def chunk_tokens(text, size=400, overlap=60):
    ids = enc.encode(text)
    step = size - overlap
    return [enc.decode(ids[i:i+size]) for i in range(0, len(ids), step)]
```

## Recipe 2 — Contextual Retrieval (the high-value add)

Prepend a 50–100 token situating blurb generated by Haiku, using the **exact Anthropic prompt**, with the
full document cached so you pay for it once.

```python
import os, anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CTX_PROMPT = """<document>
{doc}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{chunk}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

def contextualize(document: str, chunk: str) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=120,
        messages=[{
            "role": "user",
            "content": [
                # Cache the big document block → reused across every chunk of this doc.
                {"type": "text", "text": f"<document>\n{document}\n</document>",
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text",
                 "text": CTX_PROMPT.format(doc="", chunk=chunk).split("</document>",1)[1]},
            ],
        }],
    )
    return msg.content[0].text.strip()

# Enrich: the blurb goes to BOTH the embedding text and the BM25 text.
enriched = [f"{contextualize(document, c)}\n\n{c}" for c in chunks]
```

Then embed `enriched[i]` into your vector store **and** feed `enriched[i]` to your BM25/lexical index.
Keep the original `chunks[i]` around to return to the LLM if you don't want the blurb in the answer
context. Handoff to `hybrid-search-reranking` for the fusion + rerank step (top-150 → top-20).

Batch tip: iterate all chunks of one document consecutively so the cached `<document>` block stays warm
(cache TTL is ~5 min); process doc-by-doc, not chunk-interleaved across docs.

The bundled helper does this end to end: `python3 scripts/contextual_chunk.py doc.txt`.

## Recipe 3 — Late chunking (no LLM, keeps global context in the vector)

Embed the whole doc first, then mean-pool token spans into chunk vectors — so "it"/"the city" inherit
their antecedent's context.

```python
# pip install transformers torch
import torch
from transformers import AutoModel, AutoTokenizer

tok = AutoTokenizer.from_pretrained("jinaai/jina-embeddings-v2-base-en", trust_remote_code=True)
model = AutoModel.from_pretrained("jinaai/jina-embeddings-v2-base-en", trust_remote_code=True)

def late_chunk_embeddings(text, spans):        # spans: [(start_char,end_char), ...]
    enc = tok(text, return_offsets_mapping=True, return_tensors="pt")
    with torch.no_grad():
        tok_emb = model(input_ids=enc["input_ids"],
                        attention_mask=enc["attention_mask"]).last_hidden_state[0]
    offsets = enc["offset_mapping"][0].tolist()
    out = []
    for c0, c1 in spans:                        # map char span -> token index span
        idx = [i for i,(a,b) in enumerate(offsets) if a < c1 and b > c0 and b > a]
        if idx:
            out.append(tok_emb[idx].mean(dim=0).cpu().numpy())
    return out                                  # one vector per chunk, globally aware
```

Prefer the hosted route when you don't want a local model: POST to `https://api.jina.ai/v1/embeddings`
with `{"model":"jina-embeddings-v2-base-en","late_chunking":true,"input":[...sentences...]}` — it
concatenates the inputs, embeds once, and returns one late-chunked vector per input.

Late chunking and Contextual Retrieval are complementary: late chunking fixes the **embedding**;
contextual blurbs also fix **lexical/BM25** recall and the text the reranker sees. Use both on hard corpora.

## Recipe 4 — Hierarchical (parent-child)

Index small children for precise matching; return the large parent for context.

```python
parents = splitter.split_text(document)                       # ~2000-token parents
children = []
for pid, p in enumerate(parents):
    for c in chunk_tokens(p, size=300, overlap=40):
        children.append({"text": c, "parent_id": pid})
# Embed children. On hit, look up children[i]["parent_id"] and return parents[pid] to the LLM.
```

## Verify

- **Orphan test:** sample 10 enriched chunks; each must be answerable/locatable with zero external
  context. If a chunk still says "it fell 3%" with no subject, the blurb (or window) is too thin.
- **Prompt-cache is working:** check `response.usage` — `cache_read_input_tokens` should dominate from the
  2nd chunk of a document onward. If it's ~0, your `<document>` block isn't stable/large enough (min
  cacheable size applies) or you're interleaving docs.
- **Late chunking sanity:** cosine("Its population", "Berlin") should be *higher* under late chunking
  than under naive per-chunk embedding on a doc where Berlin is the antecedent.
- **Real metric:** run `llm-rag-eval-harness` (recall@k, nDCG) A/B: baseline vs +context vs +late. Ship
  the winner; don't assume.

## Pitfalls

- **Skipping prompt caching** on Contextual Retrieval → you resend the full document per chunk and cost
  ~50× more. Always cache the doc block; process a document's chunks consecutively.
- **Late chunking on a CLS-pooled model** → silently useless; it requires mean pooling.
- **Doc longer than the embed window** for late chunking → split into macro-windows (e.g. per section)
  first, late-chunk within each; you can't get global context across a boundary the model never saw.
- **Over-large chunks** dilute the embedding (one vector averaging many topics) and blow the LLM context
  budget; **over-small** chunks lose meaning. Tune against eval, not vibes.
- **Blurb only in the vector, not in BM25** → you leave the 49% lexical gain on the table. Put the
  enriched text in *both* indexes.
- **Semantic chunking with a fixed global threshold** across heterogeneous docs → wildly uneven chunks;
  use a percentile breakpoint per document.
- **Returning the blurb as answer context** when you didn't want the model to see synthesized framing —
  keep originals and swap at return time if needed.
- **Model names drift.** Confirm the current Haiku id (`claude-haiku-4-5` here) and embed-model id against
  live docs before shipping.
