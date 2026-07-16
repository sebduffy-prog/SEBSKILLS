---
name: long-doc-chunking
category: rag
description: >
  Split any long document, PDF, transcript, or source-code file into clean, structure-preserving
  chunks using Chonkie — pick token / recursive / sentence / semantic / SDPM / late / code (AST)
  / neural chunking, tune chunk_size + overlap, and keep headings, tables, and functions intact.
  Use when you ask "how do I chunk this document / PDF / codebase", "what chunk size and overlap",
  "my chunks split mid-sentence or mid-function", "semantic vs recursive chunking", "AST code
  chunking", "late chunking", or need runnable chunking code before embedding or summarizing.
when_to_use:
  - "You have a big document / PDF / markdown / transcript and need to split it into chunks before embedding"
  - "Chunks are cutting mid-sentence, mid-heading, mid-table, or mid-function and you need structure-aware splitting"
  - "Chunking a codebase and want AST/function-boundary splits instead of blind token windows"
  - "Choosing between token, recursive, sentence, semantic, SDPM, late, or neural chunking for a corpus"
  - "Picking chunk_size + overlap and want a fast, dependency-light chunker (Chonkie)"
  - "Late chunking to keep whole-document context inside each chunk vector without an LLM call"
when_not_to_use:
  - "You want per-chunk situating context prepended before embedding (Anthropic Contextual Retrieval) — use rag-chunking-contextual"
  - "Chunks are fine and you need lexical+vector fusion or a reranker — use hybrid-search-reranking"
  - "Entity/relationship graph over the corpus — use graphrag-builder"
  - "Measuring retrieval quality after chunking (recall@k, nDCG) — use llm-rag-eval-harness"
  - "Provisioning the vector DB (collections, indexes, upserts) — use vector-store-setup"
keywords: [chunking, chonkie, chunker, token chunker, recursive chunker, semantic chunker, sdpm, late chunking, code chunker, ast chunking, neural chunker, chunk size, overlap, pdf chunking, document splitting, text splitter, structure preservation, tree-sitter]
similar_to: [rag-chunking-contextual, hybrid-search-reranking, vector-store-setup, retrieval-as-context, agentic-rag-pipeline]
inputs_needed:
  - "Document type + typical length (prose PDF vs markdown vs transcript vs source code)"
  - "Downstream tokenizer / embedding model (so chunk_size is in the right token units)"
  - "Target chunk_size and overlap, or whether to auto-derive from the embed model's context window"
  - "Whether structure (headings, tables, functions) must be preserved verbatim"
produces: Runnable Chonkie chunking code plus a chosen chunker + chunk_size/overlap for the corpus, emitting Chunk objects ready to embed
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Long-Document & Code Chunking (Chonkie)

Turn one big blob — PDF text, markdown, a transcript, or a source file — into clean chunks that
respect structure. This skill uses **Chonkie** (MIT-licensed, `chonkie-inc/chonkie`): a fast,
lightweight chunking library with a uniform `chunker(text) -> list[Chunk]` call across every strategy.

Two things this skill picks for you: **which chunker** (how you cut) and **chunk_size + overlap**
(how big). For *per-chunk situating context* before embedding, that is a separate lever — see
`rag-chunking-contextual`.

## When to use

At ingest-design time, or when your current splitter mangles the source: sentences cut in half, a
markdown table sliced across two chunks, a Python function split down the middle. Those are
structure-preservation failures — the fix is a structure-aware chunker, not a bigger `chunk_size`.

## Prerequisites

```bash
pip install chonkie                 # core: TokenChunker, SentenceChunker, RecursiveChunker (no heavy deps)
pip install "chonkie[semantic]"     # SemanticChunker, SDPMChunker, LateChunker (sentence-transformers)
pip install "chonkie[code]"         # CodeChunker (tree-sitter-language-pack)
pip install "chonkie[neural]"       # NeuralChunker (fine-tuned split-point model)
pip install "chonkie[all]"          # everything
```

- Token/recursive/sentence chunking need **nothing heavy** — just a tokenizer (`"character"`,
  `"gpt2"`, `"tiktoken"`, or a HF model name).
- Semantic / SDPM / late chunking pull in `sentence-transformers` + torch.
- `CodeChunker` requires `tree-sitter-language-pack`; on first use it downloads grammars.
- Chonkie does **not** parse PDFs — extract text first (`pdfplumber`, `pymupdf`, or the `pdf` skill),
  then chunk the string.

Every chunker returns `Chunk` objects with: `text`, `start_index`, `end_index`, `token_count`,
`context` (optional), `embedding` (populated only by late chunking), `metadata`.

## Choosing a chunker

| Chunker | Cuts on | Best for | Extra deps | Notes |
|---|---|---|---|---|
| `TokenChunker` | fixed N tokens + overlap | uniform text, a baseline | none | dumb but bulletproof; start here |
| `SentenceChunker` | sentence boundaries | prose where sentences matter | none | never splits mid-sentence |
| `RecursiveChunker` | paragraph → sentence → word (recipe-driven) | markdown / mixed docs | none | **default for most corpora**; `recipe="markdown"` keeps headings |
| `SemanticChunker` | embedding-similarity drop between sentences | topic-shifting docs, transcripts | `[semantic]` | variable-size; tune `threshold` |
| `SDPMChunker` | semantic double-pass merge | docs with recurring themes far apart | `[semantic]` | merges non-adjacent similar sentences |
| `LateChunker` | recursive split **after** whole-doc embedding | keep global context in every chunk vector | `[semantic]` | emits chunk `embedding`; no LLM needed |
| `CodeChunker` | tree-sitter **AST** (functions/classes) | source code | `[code]` | never splits mid-function; `language="auto"` |
| `NeuralChunker` | fine-tuned split-point model | high-quality topic splits | `[neural]` | slowest; best boundaries |

**Defaults that rarely go wrong:** `RecursiveChunker`, `chunk_size` matched to your embed model
(~256–512 tokens for most sentence-transformers; up to 2048 for long-context models), overlap
~10–15% via the overlap refinery. Only reach for semantic/late/neural when you can *measure* they
beat recursive (use `llm-rag-eval-harness`).

## Recipe 1 — Recursive, structure-aware (start here)

```python
from chonkie import RecursiveChunker

# Recipe keeps markdown structure (headings, lists, code fences) as split boundaries.
chunker = RecursiveChunker.from_recipe("markdown", lang="en",
                                       tokenizer="gpt2", chunk_size=512)
chunks = chunker(markdown_text)          # __call__ == .chunk()

for c in chunks:
    print(c.token_count, repr(c.text[:60]))
    # c.start_index / c.end_index map back into markdown_text verbatim
```

Plain prose (no recipe): `RecursiveChunker(tokenizer="gpt2", chunk_size=512)`. It recurses
paragraph → sentence → word so a chunk only breaks mid-word as a last resort.

## Recipe 2 — Add overlap via the Pipeline refinery

Chunkers don't add overlap themselves; the `overlap` refinery does. Use the Pipeline to chunk then
refine in one pass:

```python
from chonkie import Pipeline

pipe = (Pipeline()
        .chunk_with("recursive", tokenizer="gpt2", chunk_size=512, recipe="markdown", lang="en")
        .refine_with("overlap", context_size=64))     # ~12% of 512 tokens carried between chunks

doc = pipe.run(texts=markdown_text)
chunks = doc.chunks
```

`context_size` is the overlap window (tokens). Overlap reduces answer-splitting across a boundary at
the cost of index size — 10–15% is the usual sweet spot.

## Recipe 3 — Semantic chunking (topic-shift boundaries)

```python
from chonkie import SemanticChunker

chunker = SemanticChunker(
    embedding_model="minishlab/potion-base-32M",  # default; fast static embeddings
    threshold=0.8,          # (0,1) exclusive — HIGHER = more, tighter chunks; LOWER = fewer, broader
    chunk_size=512,
    similarity_window=3,    # sentences compared when scoring a boundary
)
chunks = chunker(transcript_text)
```

Chunks vary in size — that is the point. If it over-splits, lower `threshold`; if chunks sprawl,
raise it. `SDPMChunker` has the same interface but does a second merge pass to group similar
sentences that aren't adjacent (good for docs that revisit a topic).

## Recipe 4 — Code chunking (AST, never split a function)

```python
from chonkie import CodeChunker

chunker = CodeChunker(
    language="auto",        # or "python", "typescript", "go", ... (tree-sitter-language-pack)
    tokenizer="character",
    chunk_size=2048,
    include_nodes=False,    # True to attach the parsed AST nodes to each chunk
)
chunks = chunker(open("service.py").read())
```

Splits on tree-sitter AST boundaries, so functions/classes stay whole. `language="auto"` detects via
shebang then trial-parsing. First run downloads grammars — budget a few seconds.

## Recipe 5 — Late chunking (global context in each vector, no LLM)

```python
from chonkie import LateChunker

chunker = LateChunker(
    embedding_model="nomic-ai/modernbert-embed-base",  # long-context, mean-pooled
    chunk_size=512,
)
chunks = chunker(long_document_text)
for c in chunks:
    vec = c.embedding    # already computed: token embeddings from the WHOLE doc, pooled per chunk
```

Late chunking embeds the entire document first, then pools per-chunk — so a chunk that says "it fell
3%" carries the document's global context in its vector without any LLM enrichment call. Requires a
**mean-pooled long-context** model; it's a no-op benefit on short-context or CLS-pooled models.

## Chunker-agnostic swap

Every chunker shares the call signature, so you can A/B them without touching downstream code:

```python
def get_chunker(kind: str):
    from chonkie import RecursiveChunker, SemanticChunker, CodeChunker, TokenChunker
    return {
        "token":     lambda: TokenChunker(tokenizer="gpt2", chunk_size=512),
        "recursive": lambda: RecursiveChunker(tokenizer="gpt2", chunk_size=512),
        "semantic":  lambda: SemanticChunker(chunk_size=512),
        "code":      lambda: CodeChunker(language="auto"),
    }[kind]()

chunks = get_chunker("recursive")(text)   # all return list[Chunk]
```

## Verify

- **No structure damage:** with `RecursiveChunker.from_recipe("markdown", ...)`, assert no chunk
  starts or ends inside a `|table|` row or mid-heading — spot-check `chunks[i].text`.
- **Round-trip:** `text[c.start_index:c.end_index] == c.text` for a sample chunk (indices are exact).
- **Token budget:** `max(c.token_count for c in chunks) <= chunk_size`. If a chunk exceeds it, your
  tokenizer differs from the embed model's — pass the matching tokenizer.
- **Code integrity:** for `CodeChunker`, every chunk should parse (or be a clean node group); no chunk
  should end with an unbalanced brace/`def`.
- **Distribution sanity:** `len(chunks)` and mean `token_count` are in the expected range; a huge tail
  of tiny chunks usually means `threshold`/`min_characters_per_chunk` needs tuning.

## Pitfalls

- **Wrong token units.** `chunk_size` is measured by the chunker's tokenizer. If you chunk with
  `"gpt2"` but embed with a different model, your real chunks may overflow the embed context. Pass the
  **embed model's** tokenizer (or an HF model name) to the chunker.
- **Overlap isn't built in.** Chunkers don't overlap on their own — add the `overlap` refinery
  (Recipe 2) or you get zero-overlap hard cuts.
- **PDFs aren't handled.** Chonkie chunks strings. Extract clean text first; feed it garbage (headers,
  footers, hyphenation) and you chunk garbage.
- **Semantic `threshold` is (0,1) exclusive** and inverted from intuition: higher threshold → more,
  smaller chunks. Don't pass `0` or `1`.
- **`CodeChunker` first-run latency.** It downloads tree-sitter grammars; pre-warm in a build step so
  request latency doesn't spike.
- **Late chunking needs the right model.** Use a mean-pooled long-context embedder, and remember the
  chunk `embedding` is already computed — don't re-embed and lose the global context.
- **Semantic/late/neural cost real compute.** Recursive is nearly free and usually within a couple of
  points of the fancy chunkers. Measure before paying — don't default to semantic because it sounds
  smarter.
