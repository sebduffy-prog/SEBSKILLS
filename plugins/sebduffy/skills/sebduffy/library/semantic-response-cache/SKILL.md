---
name: semantic-response-cache
category: model-routing
description: >
  Put an embedding-similarity (semantic) cache in front of an LLM or RAG app so
  near-duplicate questions reuse a stored answer and skip inference entirely —
  not just byte-identical hits like a normal KV cache. "What's France's capital?"
  and "capital city of France?" collapse to one paid call. Ships three drop-in
  paths: GPTCache (batteries-included adapter), RedisVL SemanticCache (production,
  Redis-backed), and a zero-dependency numpy cache for tests. Use when someone
  says "semantic cache", "cache similar prompts", "stop paying for repeat
  questions", "GPTCache", "RedisVL LLM cache", "vector cache for my chatbot",
  "cut LLM cost on FAQ-style traffic", or "reuse answers for paraphrased queries".
when_to_use:
  - "A chatbot/support/FAQ bot gets the same question worded many different ways"
  - "You want repeat or paraphrased prompts served free instead of re-calling the model"
  - "Latency matters and a cache hit (~ms) beats a 1-3s generation"
  - "You want to cut spend on the easy, high-volume long tail of duplicate queries"
  - "You already have Redis and want a production semantic cache (RedisVL)"
  - "You need a tunable similarity threshold to trade recall vs wrong-answer risk"
when_not_to_use:
  - "You want the cheapest MODEL per request, not answer reuse -> model-triage-router"
  - "You want to lay out a prompt so the provider's prompt cache hits -> cache-aware-context-layout"
  - "Routing across different vendors behind one endpoint -> cross-provider-gateway"
  - "Every query is unique/personalized/time-sensitive (cache never hits, risks staleness)"
  - "You just need exact-match KV caching -> a plain dict/Redis GET, no embeddings needed"
keywords: [semantic cache, gptcache, redisvl, semanticcache, llm cache, embedding cache, vector cache, similarity cache, prompt cache, cache similar queries, paraphrase cache, faiss, redis vector, cosine similarity, distance threshold, cache hit rate, cost reduction, response reuse, onnx embedding, sbert]
similar_to: [cache-aware-context-layout, model-triage-router, cross-provider-gateway, batch-api-offloader, output-token-diet, llm-cost-estimator]
inputs_needed:
  - "Where answers live now (raw LLM call, RAG chain, chatbot endpoint) so you know the wrap point"
  - "Backend: GPTCache (quick), RedisVL (prod + Redis on hand), or numpy (tests/prototype)"
  - "An embedding source: OpenAI/Cohere API key, or local ONNX/SBERT (offline, free)"
  - "A tolerance for wrong reuse -> sets the similarity threshold (strict FAQ vs loose brainstorm)"
  - "Optional TTL if answers go stale (prices, news, inventory)"
produces: A semantic-cache layer wrapping your LLM calls (GPTCache / RedisVL / numpy), returning stored answers for near-duplicate prompts and only paying for inference on genuine misses, plus hit-rate stats.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Semantic Response Cache

A normal cache only hits on a byte-identical key. A **semantic** cache embeds the
prompt and hits when a *near-duplicate* has been seen before — so paraphrases,
re-orderings, and typos of the same question all reuse one paid answer. On
FAQ/support/RAG traffic this is often the single biggest cost + latency win.

Core loop, regardless of backend:

```
embed(prompt) -> nearest stored vector -> if cosine >= threshold: return stored answer (FREE)
                                          else: call the LLM, then store(prompt, answer)
```

The whole game is the **threshold**: too loose and you serve a confidently wrong
neighbour; too strict and you never hit. Tune it on real traffic (see Verify).

## When to use

- High-volume traffic where the same intent arrives worded many ways.
- Answers are stable enough to reuse for a while (or you set a TTL).
- You care about cost/latency on the easy long tail more than novelty.

This is answer reuse. For picking a cheaper *model* per request use
`model-triage-router`; for making the *provider's* prompt cache hit use
`cache-aware-context-layout`. They stack cleanly with this.

## Prerequisites

Pick ONE backend:

| Backend | Install | Best for |
|---|---|---|
| GPTCache | `pip install gptcache` | Fastest start; drop-in OpenAI/LangChain adapters |
| RedisVL | `pip install redisvl` + Redis 8 / Redis Stack (RediSearch) | Production, shared across processes, persistence |
| numpy (bundled) | `pip install numpy` | Tests, prototypes, air-gapped, no server |

Embeddings — one of:
- **Local / free / offline:** ONNX (`GPTCache/paraphrase-albert-onnx`) or SBERT
  (`sentence-transformers`). No API cost, no data leaves the box.
- **API:** OpenAI / Cohere embeddings — one cheap embed call per lookup. Note this
  adds a network hop on every request, hit or miss.

Honesty check: a lookup costs one embedding + one vector search. That's far cheaper
than generation, but not zero — if hit rate is near 0 (every query unique), a cache
just adds latency. Measure before committing (Verify).

## Recipe A — GPTCache (fastest, local ONNX embeddings)

Batteries included: wraps the OpenAI client so `openai.ChatCompletion.create`
transparently checks the cache first. FAISS vector store + SQLite metadata, all local.

```python
from gptcache import cache
from gptcache.adapter import openai                      # GPTCache's wrapped client
from gptcache.embedding import Onnx
from gptcache.manager import CacheBase, VectorBase, get_data_manager
from gptcache.similarity_evaluation.distance import SearchDistanceEvaluation

onnx = Onnx()                                             # local paraphrase-albert model
data_manager = get_data_manager(
    CacheBase("sqlite"),
    VectorBase("faiss", dimension=onnx.dimension),
)
cache.init(
    embedding_func=onnx.to_embeddings,
    data_manager=data_manager,
    similarity_evaluation=SearchDistanceEvaluation(),     # lower distance = more similar
)
cache.set_openai_key()                                    # reads OPENAI_API_KEY

# First call misses (pays); a paraphrase of it hits (free):
resp = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
)
print(resp["choices"][0]["message"]["content"])
```

Notes: to cache **your own** LLM (Claude, local model), don't use the OpenAI adapter —
call `cache.import_data`/the `get`/`put` primitives, or use Recipe B/C which are
model-agnostic. GPTCache development has slowed; for new production work prefer RedisVL.

## Recipe B — RedisVL SemanticCache (production, Redis-backed)

Model-agnostic and shared across every process/worker pointing at the same Redis.
`distance_threshold` is COSINE distance in `[0, 2]` — **lower = stricter** (opposite
of a similarity score).

```python
from redisvl.extensions.cache.llm import SemanticCache   # older ver: redisvl.extensions.llmcache
from redisvl.utils.vectorize import HFTextVectorizer      # local SBERT, free/offline

llmcache = SemanticCache(
    name="llmcache",
    redis_url="redis://localhost:6379",
    distance_threshold=0.1,                                # start strict; raise to hit more
    vectorizer=HFTextVectorizer("redis/langcache-embed-v1"),
)

def ask(prompt: str) -> str:
    hit = llmcache.check(prompt=prompt, num_results=1)
    if hit:
        return hit[0]["response"]                          # FREE
    answer = call_your_llm(prompt)                         # miss -> pay
    llmcache.store(prompt=prompt, response=answer)
    return answer

# Widen at runtime if hit rate is too low:
llmcache.set_threshold(0.2)
```

Add a TTL for staleable answers: `SemanticCache(..., ttl=3600)` expires entries after
1h. RedisVL also ships a `CacheThresholdOptimizer` to fit the threshold to a labelled
set — use it once you have ~30+ labelled pos/neg pairs.

## Recipe C — Zero-dependency numpy cache (tests / prototype / air-gapped)

Bundled `scripts/semantic_cache.py`. No server, no vector DB — vectors live in an
in-process numpy matrix (fine to ~50k entries), optional JSON persistence. Threshold
here is a **cosine similarity floor** (higher = stricter), the intuitive direction.

```python
from scripts.semantic_cache import SemanticCache

def embed(text):                       # plug in OpenAI, SBERT, ONNX -> np.ndarray
    return get_embedding(text)

cache = SemanticCache(embed_fn=embed, threshold=0.90, ttl_seconds=3600)

def ask(prompt):
    hit = cache.get(prompt)
    if hit is not None:
        return hit
    answer = call_your_llm(prompt)
    cache.set(prompt, answer)
    return answer

cache.save("cache.json")               # persist; cache.load(...) to restore
print(cache.stats())                   # {'entries': N, 'total_hits': M}
```

Self-test it: `python3 scripts/semantic_cache.py` -> `self-test OK ...`.

## Threshold tuning (the part that actually matters)

1. Log real prompts. Build ~30-100 pairs labelled *should-hit* (true paraphrases) vs
   *should-miss* (different intent, same topic).
2. Sweep the threshold; measure **false-hit rate** (served a wrong neighbour) and
   **hit rate**. False hits are the dangerous failure — a confidently wrong cached answer.
3. Pick the strictest threshold that keeps hit rate worthwhile. FAQ/support: lean strict.
   Brainstorm/low-stakes: lean loose.
4. Guard staleness with a TTL when answers change (prices, news, stock, dated facts).

## Verify

- **It hits:** store a prompt, query a paraphrase, confirm a hit with no LLM call
  (log/trace the miss path, or watch provider request count stay flat).
- **It doesn't over-hit:** query an unrelated same-topic prompt; confirm a MISS.
- **Hit rate is real:** shadow it over a day of traffic and log
  `hits / (hits + misses)`. Below ~10-15%, the embedding hop may not pay off — reconsider
  or narrow to a known-repetitive endpoint.
- **RedisVL/Redis:** `redis-cli ping` -> `PONG`, and `FT._LIST` shows the cache index.

## Pitfalls

- **Threshold too loose = wrong answers served confidently.** The #1 failure. Start
  strict, loosen with evidence. RedisVL distance is *inverted* vs a similarity score.
- **Personalization / context leak.** If answers depend on user, tenant, locale, or
  session, bake that into the cache key/namespace or you'll serve one user another's
  answer. Namespace by tenant.
- **Staleness.** Time-sensitive answers need a TTL or explicit invalidation; a cache
  happily serves last week's price forever.
- **Caching non-deterministic-by-design output.** If variety is the point (creative
  drafts, high temperature), a cache kills it — don't cache those routes.
- **Embedding cost/latency on misses.** Every lookup pays one embed. With API
  embeddings that's a network hop per request; prefer local ONNX/SBERT for hot paths.
- **Cache poisoning.** You store whatever the LLM returned — a bad/hallucinated answer
  gets reused. Consider only caching after a validation/guardrail pass.
- **GPTCache staleness.** Great for a quick spike; for long-lived production prefer
  RedisVL (active) or the numpy path you fully control.
