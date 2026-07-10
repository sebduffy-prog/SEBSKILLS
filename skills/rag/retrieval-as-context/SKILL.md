---
name: retrieval-as-context
category: rag
description: >
  Turn a pile of retrieved chunks into clean, ordered, citation-ready LLM context. Covers query
  rewrite / HyDE hypothetical-document expansion to close the query↔doc gap, cross-encoder rerank,
  cross-source dedup / near-dup collapse, token-budget packing, and reorder to beat lost-in-the-middle
  (best chunks at the head AND tail). Use when your RAG "retrieves the right stuff but answers badly",
  when you ask "how do I order retrieved documents", "HyDE", "query expansion for retrieval",
  "dedupe retrieved chunks", "lost in the middle", "make retrieval citation-ready", or "context packing".
when_to_use:
  - "Retrieval returns relevant chunks but the LLM's answer is vague, wrong, or ignores them"
  - "You want to add HyDE / query rewrite to close the gap between short queries and long docs"
  - "Retrieved set has duplicates or near-duplicates from overlapping chunks / multiple sources"
  - "You must fit N chunks into a fixed token budget and decide what to drop and in what order"
  - "Answers cite nothing or cite wrong; you need each chunk tagged so the model can attribute sources"
  - "You suspect 'lost in the middle' — the key passage is buried in the middle of a long prompt"
when_not_to_use:
  - "You need the lexical+vector fusion + first-stage reranker itself — use hybrid-search-reranking"
  - "Chunks retrieve badly at the source (orphan fragments, bad splits) — fix ingest with rag-chunking-contextual"
  - "Multi-hop retrieve→reason→retrieve agent loops — use agentic-rag-pipeline"
  - "Measuring whether any of this helped (recall@k, faithfulness, nDCG) — use llm-rag-eval-harness"
  - "Entity/relationship graph retrieval — use graphrag-builder"
keywords: [hyde, hypothetical document embeddings, query rewrite, query expansion, rerank, cross-encoder, dedup, deduplication, near-duplicate, lost in the middle, context ordering, reorder, long context reorder, context packing, token budget, citation, ruler, mmr, context engineering, rag context]
similar_to: [hybrid-search-reranking, rag-chunking-contextual, agentic-rag-pipeline, llm-rag-eval-harness, long-doc-chunking]
inputs_needed:
  - "The raw retrieved set (chunks + scores + source/doc ids + any metadata)"
  - "Target model context budget for retrieval (tokens you'll spend on chunks, not the whole window)"
  - "Whether an LLM key is available for HyDE / query rewrite, and a reranker (Cohere / local cross-encoder)"
  - "Whether the answer must be citation-ready (do sources need visible ids?)"
produces: An ordered, deduped, token-budgeted, citation-tagged context block plus the query-transform + rerank code that built it
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Retrieval as Context

Retrieval getting the right chunks is only half the job. The other half is **shaping those chunks into
context the model actually uses**. This skill is the stage *between* your retriever and your generation
prompt. Five levers, applied in order:

1. **Query transform** (before retrieval) — rewrite the query / HyDE, so what you search with matches how
   answers are written.
2. **Rerank** — cross-encoder scores each (query, chunk) pair; keep the true top-k.
3. **Dedup** — collapse near-duplicates from overlapping chunks and multiple sources.
4. **Pack** — fit the survivors into a token budget; drop the weakest.
5. **Order** — place the strongest chunks at the **head and tail** to beat lost-in-the-middle, and tag
   each with a citation id.

## When to use

Reach for this when retrieval *quality* is fine but answer *quality* is not: the right passage is in the
retrieved set but the model talks past it, hallucinates around it, or cites nothing. That's a
context-shaping problem, not a retriever problem. If chunks themselves are bad (orphaned "it fell 3%"
fragments), fix ingest first with `rag-chunking-contextual`.

## Prerequisites

- **HyDE / query rewrite:** any chat LLM (`pip install anthropic` or `openai`) + a key. HyDE also needs
  your existing embedder — you embed the *hypothetical answer*, not the query.
- **Rerank:** one of
  - Cohere Rerank API — `pip install cohere`, `COHERE_API_KEY` (model `rerank-v3.5`), or
  - a local cross-encoder — `pip install sentence-transformers` (e.g.
    `cross-encoder/ms-marco-MiniLM-L-6-v2`, CPU-fine; `BAAI/bge-reranker-v2-m3` for quality).
- **Token counting for packing:** `pip install tiktoken` (approximate for non-OpenAI models is fine).
- Everything else (dedup, order) is dependency-free stdlib.

The lost-in-the-middle effect (Liu et al., *TACL* 2023) and long-context benchmarks like **RULER** (NVIDIA)
both show models use the *start* and *end* of long inputs far better than the middle, and that a model's
*effective* context is well under its advertised window — so ordering and pruning are not optional polish.

## Recipe 1 — HyDE (close the query↔document gap)

Short queries live in a different region of embedding space than the long documents that answer them. HyDE
asks the LLM to hallucinate a *plausible answer document*, then retrieves with **that** embedding. It needs
no labels and no fine-tuning (Gao et al., 2022).

```python
import os, anthropic
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

HYDE_PROMPT = ("Write a short, factual passage that directly answers the question as if it were an "
               "excerpt from a relevant document. Invent specific-sounding details; correctness is not "
               "required — it is only used to improve retrieval.\n\nQuestion: {q}\nPassage:")

def hyde_query(question: str) -> str:
    msg = client.messages.create(
        model="claude-haiku-4-5", max_tokens=200,
        messages=[{"role": "user", "content": HYDE_PROMPT.format(q=question)}],
    )
    return msg.content[0].text.strip()

# Retrieve with the hypothetical answer's embedding (optionally averaged with the real query's).
hypo = hyde_query(user_query)
query_vec = embed(hypo)                       # your existing embedder
# Robust variant: mean of a few hypotheticals + the raw query to reduce a single bad hallucination.
# query_vec = mean([embed(hyde_query(user_query)) for _ in range(3)] + [embed(user_query)])
results = vector_store.search(query_vec, top_k=100)
```

When HyDE helps: knowledge-heavy, well-populated corpora where answers are written in a different register
than questions. When it hurts: very sparse/novel corpora (the hallucination has no real neighbour) and
keyword-exact lookups (IDs, error codes) — there, a plain **query rewrite** (expand acronyms, add
synonyms, split multi-part questions) is safer than a full hypothetical.

## Recipe 2 — Rerank to true top-k

First-stage retrieval optimises recall (grab 50–100). A cross-encoder reads query and chunk *together* and
scores relevance far more accurately than the bi-encoder similarity did. Keep the top ~5–10.

```python
# Cohere hosted
import cohere
co = cohere.ClientV2(os.environ["COHERE_API_KEY"])
def rerank(query, docs, top_n=8):             # docs: list[str]
    r = co.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=top_n)
    return [(x.index, x.relevance_score) for x in r.results]   # sorted, best first
```

```python
# Local cross-encoder (no API, no key)
from sentence_transformers import CrossEncoder
ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
def rerank_local(query, docs, top_n=8):
    scores = ce.predict([(query, d) for d in docs])
    order = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:top_n]
    return [(i, float(scores[i])) for i in order]
```

Rerank with the **original user query**, not the HyDE text — the cross-encoder wants the real intent.
Already have fusion + a first reranker in place? That's `hybrid-search-reranking`'s job; this skill assumes
you hand it a candidate set and refine from there.

## Recipe 3 — Dedup / collapse near-duplicates

Overlapping chunks and multi-source corpora produce the same fact three times, wasting budget and biasing
the model. Collapse exact and near-duplicates, keeping the highest-ranked instance.

```python
import re
from difflib import SequenceMatcher

def _norm(t): return re.sub(r"\s+", " ", t.lower()).strip()

def dedup(ranked, sim_threshold=0.85):
    """ranked: list of dicts {text, score, source} sorted best-first. Keeps first (best) of each cluster."""
    kept = []
    for item in ranked:
        n = _norm(item["text"])
        dup = False
        for k in kept:
            # containment (chunk overlap) OR high fuzzy similarity
            if n in _norm(k["text"]) or _norm(k["text"]) in n or \
               SequenceMatcher(None, n, _norm(k["text"])).ratio() >= sim_threshold:
                dup = True
                break
        if not dup:
            kept.append(item)
    return kept
```

For large sets, `SequenceMatcher` is O(n²) and slow — switch to MinHash/SimHash (`datasketch`) or dedup on
embedding cosine (>0.95) instead. When two near-dups come from *different* sources, keep the best but stash
the other source ids so a claim can cite both.

## Recipe 4 — Pack to a token budget

Decide what actually fits. Greedily admit best-first until the budget is spent; never truncate a chunk
mid-sentence (a half-chunk is often worse than none).

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
def ntok(s): return len(enc.encode(s))

def pack(ranked, budget_tokens=3000, per_chunk_overhead=8):
    out, used = [], 0
    for item in ranked:                       # already deduped + rerank-sorted
        cost = ntok(item["text"]) + per_chunk_overhead
        if used + cost > budget_tokens:
            continue                          # skip, try smaller later chunks (don't hard-break)
        out.append(item); used += cost
    return out, used
```

Budget is the tokens you *choose* to spend on retrieval, not the model's max window. More is not better:
past a handful of strong chunks, extra context dilutes attention and invites the lost-in-the-middle failure.

## Recipe 5 — Order + citation-tag (beat lost-in-the-middle)

Attention is strongest at the **start and end** of the prompt. Interleave so the two best chunks sit at the
head and tail and the weakest land in the middle where they'll be skimmed anyway. Tag each with a stable id
so the model can cite.

```python
def order_for_attention(packed):
    """Strongest at both ends, weakest in the middle (packed is best-first)."""
    head, tail = [], []
    for i, item in enumerate(packed):
        (head if i % 2 == 0 else tail).append(item)   # 0,2,4.. -> head; 1,3,5.. -> tail
    return head + tail[::-1]                            # tail reversed so rank-2 ends up last

def build_context(packed):
    ordered = order_for_attention(packed)
    blocks = []
    for i, item in enumerate(ordered, 1):
        src = item.get("source", f"doc{i}")
        blocks.append(f"[{i}] (source: {src})\n{item['text'].strip()}")
    return "\n\n".join(blocks)
```

Then instruct the generator explicitly: *"Answer using only the numbered sources below. Cite the ones you
use as `[n]`. If the sources don't contain the answer, say so."* Citation-readiness is a prompt contract +
the visible `[n]` ids — without the ids the model has nothing stable to point at.

## End-to-end

```python
hypo      = hyde_query(user_query)                     # 1. transform
cands     = vector_store.search(embed(hypo), top_k=100)
idxs      = rerank(user_query, [c["text"] for c in cands], top_n=15)   # 2. rerank (real query)
ranked    = [ {**cands[i], "score": s} for i, s in idxs ]
deduped   = dedup(ranked)                              # 3. dedup
packed, _ = pack(deduped, budget_tokens=3000)          # 4. pack
context   = build_context(packed)                      # 5. order + cite
# -> drop `context` into your generation prompt
```

## Verify

- **Needle test:** hide a known answer sentence in exactly ONE retrieved chunk, run the pipeline, force it
  to the *middle* of the ordered context, and confirm the model still uses it. If it's dropped only when
  central, your ordering/pruning is doing real work.
- **HyDE A/B:** recall@k with query-embedding vs HyDE-embedding on a held-out question set (via
  `llm-rag-eval-harness`). Ship HyDE only if it wins on *your* corpus — it regresses on sparse/keyword ones.
- **Dedup sanity:** count chunks before/after; eyeball that no *distinct* fact was collapsed (threshold too
  low merges different facts; too high leaves dups).
- **Budget honoured:** assert `used <= budget_tokens` and that no chunk was truncated mid-sentence.
- **Citation contract:** every `[n]` the model emits must exist in the context; grep the answer's citations
  against the ids you tagged.

## Pitfalls

- **Reranking with the HyDE text instead of the real query** — the cross-encoder then optimises for a
  hallucination. Transform for *retrieval*, rerank with the *user's* words.
- **Trusting a single HyDE hypothetical** — one bad hallucination poisons retrieval. Average a few, or
  blend with the raw query embedding.
- **HyDE on keyword-exact lookups** (error codes, SKUs, names) — it smears the exact token away. Use plain
  query rewrite there, or skip the transform.
- **Skipping dedup** — three copies of one fact eat budget and make the model over-weight it as "consensus".
- **Ordering best-first and stopping** — that buries chunk #2..#k in the low-attention middle. Bracket the
  ends (Recipe 5) or at minimum put the single best chunk *last*.
- **Filling the whole window** — more retrieved text past a few strong chunks lowers answer quality
  (lost-in-the-middle + dilution). Spend a deliberate budget, not the max window.
- **No stable ids** — "cite your sources" with unlabelled blobs yields invented citations. Tag `[n]` first.
- **O(n²) fuzzy dedup at scale** — fine for tens of chunks, unusable for thousands; move to MinHash or
  embedding-cosine dedup.
- **Model/id drift** — confirm the live Haiku id and Cohere rerank model (`rerank-v3.5`) before shipping.
```
