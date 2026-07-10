---
name: agentic-rag-pipeline
category: rag
description: >
  Build an agentic retrieval loop instead of one fixed top-k fetch — decompose the query, route
  sub-questions to the right source, grade every retrieved doc for relevance, and rewrite-and-retry
  or fall back to web search when retrieval is weak (Corrective RAG / CRAG), plus generation-time
  self-checks for hallucination and answer-completeness (Self-RAG). Use when RAG returns confidently
  wrong or off-topic answers and you ask "how do I make retrieval self-correcting", "corrective RAG",
  "self-RAG", "grade my retrieved documents", "query rewriting loop", "agentic RAG", or "LangGraph RAG".
when_to_use:
  - "One-shot retrieve-then-generate returns confident but wrong/off-topic answers and you want the system to notice and retry"
  - "Building a retrieval loop that grades docs, rewrites the query on a miss, and falls back to web search (Corrective RAG)"
  - "Adding generation-time self-checks: is the answer grounded in the docs (hallucination) and does it actually answer the question (Self-RAG)"
  - "Queries are multi-part and need decomposing into sub-questions routed to different sources"
  - "You have a working vector store + reranker and want the orchestration/agent layer on top"
  - "Implementing CRAG or Self-RAG as a LangGraph state machine"
when_not_to_use:
  - "You just need lexical+vector fusion and a reranker for a single fetch — use hybrid-search-reranking"
  - "Deciding chunk size / adding contextual blurbs at ingest — use rag-chunking-contextual"
  - "Entity/relationship graph traversal retrieval — use graphrag-builder"
  - "Measuring whether the loop actually helps (recall@k, faithfulness, nDCG) — use llm-rag-eval-harness"
  - "Provisioning the vector DB (collections, indexes, upserts) — use vector-store-setup"
  - "Just stuffing already-retrieved passages into a prompt — use retrieval-as-context"
keywords: [agentic rag, corrective rag, crag, self-rag, self reflective rag, document grading, retrieval evaluator, query rewriting, query decomposition, query routing, hallucination grader, langgraph, retrieval loop, adaptive rag, web search fallback, relevance grader, rewrite retry, reflection tokens]
similar_to: [hybrid-search-reranking, rag-chunking-contextual, graphrag-builder, llm-rag-eval-harness, retrieval-as-context]
inputs_needed:
  - "An existing retriever (vector store + optional reranker) the loop can call, and its top-k"
  - "An LLM for the grader nodes (a cheap/fast model like Haiku is ideal for grading)"
  - "Whether a web-search fallback is allowed, and which provider (Tavily / Brave / SerpAPI) + API key"
  - "Latency/cost budget — every extra loop is another LLM call, so cap the retries"
produces: A runnable LangGraph agentic-RAG state machine that grades docs, rewrites-and-retries, falls back to web search, and self-checks generations for grounding + completeness
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Agentic RAG Pipeline (Corrective RAG + Self-RAG)

Stop trusting a single top-k fetch. Wrap retrieval in a **loop with graders**: grade each retrieved
doc, and when retrieval is weak, *do something about it* — rewrite the query and retry, or fall back to
web search — before generating. Then grade the generation itself for grounding and completeness.

Two named methods, both implementable as a small state machine:

- **Corrective RAG / CRAG** (arXiv:2401.15884) — a lightweight **retrieval evaluator** scores docs and
  picks one of three actions: **Correct** (refine + keep), **Incorrect** (discard all → web search),
  **Ambiguous** (do both). Refinement = a *decompose-then-recompose* pass that keeps relevant knowledge
  strips and drops noise. Plug-and-play over any existing RAG.
- **Self-RAG** (arXiv:2310.11511) — the model emits **reflection tokens**: `Retrieve` (do I even need to
  retrieve?), `ISREL` (is this passage relevant?), `ISSUP` (is my claim supported by it?), `ISUSE` (is the
  answer useful?). You don't need their fine-tuned model — reproduce each token as a cheap **LLM-grader
  node** on any model.

In practice you build one graph that borrows from both: **CRAG's corrective retrieval + Self-RAG's
generation self-checks**. That is the LangGraph "agentic RAG" pattern below.

## When to use

Reach for this when the failure mode is *the retriever fed the LLM the wrong stuff and nobody noticed* —
confident answers about the wrong document, or "I don't know" when the answer is retrievable under a
reworded query. If your single-fetch recall is already good and only ranking is off, you want
`hybrid-search-reranking`, not this. Add the loop **after** you have a decent retriever, not instead of one.

## Prerequisites

- **Retriever:** any callable returning docs — a `vector-store-setup` collection, ideally already fused +
  reranked (`hybrid-search-reranking`). The loop is only as good as the retriever it corrects.
- **Grader LLM:** `pip install langchain-anthropic langchain-core langgraph`. Graders are tiny
  classification calls — use a **fast, cheap model** (Claude Haiku) with **structured output** so you get a
  clean `yes`/`no`, never prose to parse. Set `ANTHROPIC_API_KEY`.
- **Web-search fallback (CRAG "Incorrect" branch):** `pip install langchain-tavily` + `TAVILY_API_KEY`
  (or Brave / SerpAPI). Optional but this is the whole point of *Corrective* RAG.
- **Cost reality:** each loop adds grader + possible rewrite + re-retrieve calls. Cap retries (default
  **1 rewrite**, then answer with best-effort or web results). Grade in **one batched call** where you can.

## The graph (nodes + edges)

```
question → retrieve → grade_documents ─┬─ enough relevant docs? → generate
                                       └─ too few? → transform_query → retrieve   (retry)
                                                   └─ retries spent → web_search → generate
generate → grade_generation ─┬─ not grounded (hallucination) → generate   (regenerate)
                             ├─ not useful → transform_query               (rewrite & loop)
                             └─ grounded + useful → DONE
```

- `grade_documents` = Self-RAG **ISREL** per doc → filter. If too few survive, CRAG says the retrieval is
  **Incorrect/Ambiguous** → `transform_query` / `web_search`.
- After `generate`, two more graders: **ISSUP** (hallucination: is every claim grounded in the docs?) and
  **ISUSE** (does it answer the question?). Fail grounding → regenerate; fail usefulness → rewrite query.

## Recipe — LangGraph CRAG + Self-RAG loop

Graders first (structured output = no fragile parsing):

```python
# pip install langgraph langchain-anthropic langchain-core langchain-tavily
import os
from typing import List, TypedDict
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

FAST = ChatAnthropic(model="claude-haiku-4-5", temperature=0)   # graders + rewrite
BIG  = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)  # final generation

class YesNo(BaseModel):
    binary_score: str = Field(description="'yes' or 'no'")

def grader(system: str, human: str):
    prompt = ChatPromptTemplate.from_messages([("system", system), ("human", human)])
    return prompt | FAST.with_structured_output(YesNo)

relevance = grader(                                   # Self-RAG ISREL / CRAG evaluator
    "You grade whether a retrieved document is relevant to the user question. "
    "If it contains keywords or meaning related to the question, grade 'yes'. Be lenient — "
    "the goal is to filter obvious noise, not to be strict.",
    "Document:\n\n{document}\n\nQuestion: {question}")
grounded = grader(                                    # Self-RAG ISSUP (hallucination)
    "You grade whether an answer is grounded in / supported by the given facts. "
    "'yes' means every claim is supported by the facts.",
    "Facts:\n\n{documents}\n\nAnswer: {generation}")
answers = grader(                                      # Self-RAG ISUSE
    "You grade whether an answer actually resolves the question.",
    "Question: {question}\n\nAnswer: {generation}")

rewrite = (ChatPromptTemplate.from_messages([
    ("system", "Rewrite the question to be better optimized for retrieval. "
               "Reason about the underlying intent and produce one improved query."),
    ("human", "Original: {question}\nImproved query:")]) | FAST)
```

Now the state machine:

```python
from langgraph.graph import StateGraph, START, END
from langchain_tavily import TavilySearch

web = TavilySearch(max_results=3)
MAX_REWRITES = 1

class S(TypedDict):
    question: str
    documents: List[Document]
    generation: str
    rewrites: int

def retrieve(s):
    docs = my_retriever.invoke(s["question"])          # <-- your vector/hybrid retriever
    return {"documents": docs}

def grade_documents(s):                                # ISREL: keep only relevant
    kept = [d for d in s["documents"]
            if relevance.invoke({"document": d.page_content,
                                 "question": s["question"]}).binary_score == "yes"]
    return {"documents": kept}

def transform_query(s):
    q = rewrite.invoke({"question": s["question"]}).content
    return {"question": q, "rewrites": s.get("rewrites", 0) + 1}

def web_search(s):                                     # CRAG "Incorrect" fallback
    res = web.invoke({"query": s["question"]})
    hits = res["results"] if isinstance(res, dict) else res
    return {"documents": s["documents"] + [Document(page_content=r["content"]) for r in hits]}

def generate(s):
    ctx = "\n\n".join(d.page_content for d in s["documents"])
    ans = BIG.invoke(f"Answer using ONLY the context.\n\nContext:\n{ctx}\n\nQ: {s['question']}")
    return {"generation": ans.content}

# --- conditional edges ---
def decide_after_grading(s):                           # enough good docs? else correct
    if s["documents"]:
        return "generate"
    if s.get("rewrites", 0) < MAX_REWRITES:
        return "transform_query"                       # rewrite & retry
    return "web_search"                                # give up rewriting → web fallback

def grade_generation(s):                               # ISSUP then ISUSE
    facts = "\n\n".join(d.page_content for d in s["documents"])
    if grounded.invoke({"documents": facts, "generation": s["generation"]}).binary_score != "yes":
        return "not_grounded"                          # hallucination → regenerate
    if answers.invoke({"question": s["question"], "generation": s["generation"]}).binary_score == "yes":
        return "useful"
    return "not_useful"                                # rewrite query & loop

g = StateGraph(S)
for name, fn in [("retrieve", retrieve), ("grade_documents", grade_documents),
                 ("transform_query", transform_query), ("web_search", web_search),
                 ("generate", generate)]:
    g.add_node(name, fn)

g.add_edge(START, "retrieve")
g.add_edge("retrieve", "grade_documents")
g.add_conditional_edges("grade_documents", decide_after_grading,
    {"generate": "generate", "transform_query": "transform_query", "web_search": "web_search"})
g.add_edge("transform_query", "retrieve")              # retry the loop
g.add_edge("web_search", "generate")
g.add_conditional_edges("generate", grade_generation,
    {"not_grounded": "generate", "not_useful": "transform_query", "useful": END})

app = g.compile()
print(app.invoke({"question": "…", "rewrites": 0})["generation"])
```

Swap `my_retriever` for your `hybrid-search-reranking` retriever. That's it — a self-correcting loop.

## Recipe — query decomposition + routing (adaptive front door)

Before the loop, split a compound question and route each part. Cheap, high-leverage on multi-part queries.

```python
class SubQs(BaseModel):
    sub_questions: List[str] = Field(description="1-4 atomic sub-questions")

decompose = (ChatPromptTemplate.from_messages([
    ("system", "Break the question into the minimal set of atomic sub-questions needed to answer it. "
               "If already atomic, return it unchanged."),
    ("human", "{question}")]) | FAST.with_structured_output(SubQs))

class Route(BaseModel):
    source: str = Field(description="'vectorstore' for domain docs, 'web' for recent/general facts")

router = (ChatPromptTemplate.from_messages([
    ("system", "Route the question to 'vectorstore' (indexed domain corpus) or 'web' (current events / "
               "general knowledge outside the corpus)."),
    ("human", "{question}")]) | FAST.with_structured_output(Route))

# for sq in decompose.invoke({"question": q}).sub_questions:
#     src = router.invoke({"question": sq}).source
#     docs = (my_retriever if src == "vectorstore" else web).invoke(sq)
```

Answer each sub-question with the loop above, then compose. This is the "Adaptive RAG" pattern; keep the
decomposition shallow (≤4) or latency explodes.

## Verify

- **Grader sanity:** feed one obviously-irrelevant doc + one relevant → `relevance` must return `no`/`yes`
  respectively. If graders always say `yes`, your prompt is too lenient and the loop never corrects.
- **Correction actually fires:** ask a question whose answer needs a reworded query; assert the trace hits
  `transform_query` (inspect `app.stream(...)` events) and that the rewrite differs from the original.
- **Web fallback triggers** on an out-of-corpus question → trace hits `web_search`, final answer cites web
  content. If it never does, your relevance grader is passing junk.
- **Grounding gate works:** temporarily force `generate` to append a made-up sentence → `grade_generation`
  returns `not_grounded` and regenerates. No infinite loop (cap regenerations if paranoid).
- **Does it beat one-shot?** A/B the loop vs plain retrieve-then-generate on your eval set with
  `llm-rag-eval-harness` (faithfulness + answer-correctness). Only ship the loop if it wins — it costs more.

## Pitfalls

- **No retry cap → infinite loops / cost blowups.** `transform_query`↔`retrieve` and `generate` self-loops
  must be bounded (`MAX_REWRITES`, a regeneration counter). Always ceiling the recursion.
- **Grading with a slow/expensive model.** Graders run per-doc and per-turn; use Haiku with structured
  output. Grade all docs in one batched call when latency matters.
- **Parsing grader prose instead of structured output.** `with_structured_output(YesNo)` — never regex a
  free-text "the document seems relevant…".
- **Over-strict relevance grader** filters everything → every query falls to web search (or empty context).
  Bias the ISREL prompt toward *lenient* — its job is to drop obvious noise, not to rank.
- **Skipping the retriever quality step.** Agentic loops *correct* a decent retriever; they can't rescue a
  broken one. Fix chunking (`rag-chunking-contextual`) + fusion/rerank (`hybrid-search-reranking`) first.
- **Web fallback without provenance.** Tag web docs so the answer can cite them and you can tell corpus vs
  web at eval time; mixing silently hides where a wrong answer came from.
- **Assuming Self-RAG needs the fine-tuned model.** You do not — the reflection tokens are reproduced here
  as ordinary grader nodes on any LLM. The paper's model is one implementation, not a requirement.
- **Model-id drift.** Confirm the current Haiku/Sonnet ids and LangGraph/`langchain-tavily` import paths
  against live docs before shipping — these packages rename fast.
