---
name: embedding-corpus-clustering
category: data-analysis
description: >
  Turn a pile of unlabeled text (docs, tickets, reviews, headlines, transcripts, survey
  verbatims) into interpretable topics/clusters using sentence-transformer embeddings +
  UMAP + HDBSCAN via BERTopic, then auto-name each topic with c-TF-IDF, KeyBERTInspired, or
  an LLM. Use when you must discover structure with no labels, cluster millions of rows,
  reduce topic sprawl, assign new docs to existing topics, or build a topics-over-time view.
  Grounds every call against the real BERTopic API — reproducible, saveable, incremental.
when_to_use:
  - You have thousands-to-millions of unlabeled text records and need interpretable themes
  - You want each cluster automatically named/summarised, not just numbered
  - You need to fit once then assign new incoming documents to existing topics (.transform)
  - You want topics-over-time, per-class topics, or hierarchical topic reduction
  - Naive TF-IDF/LDA topic modelling gives incoherent or overlapping topics
when_not_to_use:
  - You already have labels and want a classifier — use zero-shot-auto-tagging instead
  - The goal is removing near-duplicate rows, not theming them — use corpus-dedup-pipeline
  - You only need exact/semantic search over the corpus — use incremental-content-index
  - Rows are images not text — use perceptual-image-dedup or a CLIP pipeline
  - Fewer than ~200 docs — clustering is unstable; read them or use an LLM to theme directly
keywords: [bertopic, topic-modeling, clustering, embeddings, sentence-transformers, umap, hdbscan, c-tf-idf, unsupervised, keybert, text-mining, dimensionality-reduction]
similar_to: [zero-shot-auto-tagging, corpus-dedup-pipeline, incremental-content-index, magika-file-triage, exploratory-data-analysis]
inputs_needed: Path to the corpus (CSV/parquet/jsonl/txt-dir) + the text column name; rough target number of topics (or "auto"); whether an OpenAI/Anthropic key is available for LLM topic names; whether new docs must be assigned later.
produces: A fitted, saved BERTopic model plus a topic table (id, name, size, keywords, representative docs) and per-document topic assignments as CSV/parquet.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Embedding Corpus Clustering (BERTopic)

Discover interpretable topics in unlabeled text at scale. Pipeline:
**embed → reduce (UMAP) → cluster (HDBSCAN) → tokenize → c-TF-IDF → (optional LLM name)**.
BERTopic wires these five swappable stages together and is MIT-licensed.

## When to use
Unlabeled text, and you need themes a human can read — support tickets, reviews, survey
verbatims, news, transcripts, docs. If you have labels, or only need search/dedup, see the
`when_not_to_use` alternatives above.

## Prerequisites (honest)
- **Python 3.9 works.** `pip install bertopic` pulls sentence-transformers, umap-learn,
  hdbscan, scikit-learn. First run downloads the embedding model (~90MB for the default
  `all-MiniLM-L6-v2`) — needs network once, then cached under `~/.cache/`.
- **hdbscan / umap-learn compile C extensions.** On this Mac (no brew) they ship prebuilt
  wheels for arm64 py3.9, so `pip install` normally just works. If a build fails, `pip
  install --only-binary=:all: hdbscan umap-learn`.
- **Memory**: embedding is the cost. ~1M short docs × 384-dim float32 ≈ 1.5GB. Embed in
  batches; for >2M rows compute embeddings once, cache to disk, and pass them in.
- **LLM naming is optional** and needs an API key (`OPENAI_API_KEY`). c-TF-IDF and
  KeyBERTInspired need no key and no network.
- No GPU required. GPU (if present) makes embedding ~10× faster via `device="cuda"`.

## Recipe 1 — Baseline fit (sane, reproducible)

Defaults are stochastic (UMAP). Pin `random_state` and pre-compute embeddings so the same
corpus gives the same topics.

```python
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer

df = pd.read_parquet("corpus.parquet")            # <- your data
docs = df["text"].fillna("").astype(str).tolist()

# 1. Embed once (cache these — the expensive step)
embedder = SentenceTransformer("all-MiniLM-L6-v2")
emb = embedder.encode(docs, batch_size=256, show_progress_bar=True)

# 2. Reproducible reducer + clusterer
umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0,
                  metric="cosine", random_state=42)
hdbscan_model = HDBSCAN(min_cluster_size=50, metric="euclidean",
                        cluster_selection_method="eom", prediction_data=True)

# 3. Cleaner keywords: drop stopwords, require a word appear in >=5 docs
vectorizer_model = CountVectorizer(stop_words="english", min_df=5, ngram_range=(1, 2))

topic_model = BERTopic(
    embedding_model=embedder,
    umap_model=umap_model,
    hdbscan_model=hdbscan_model,
    vectorizer_model=vectorizer_model,
    calculate_probabilities=False,   # True is slow on big corpora
    verbose=True,
)
topics, _ = topic_model.fit_transform(docs, embeddings=emb)

info = topic_model.get_topic_info()               # topic, Count, Name, Representation
print(info.head(20))
df["topic"] = topics                              # -1 == outliers/noise
```

`min_cluster_size` is the single most important knob: **bigger → fewer, larger topics**.
Topic `-1` is HDBSCAN noise (unassigned) — expect 10–40%. Reduce it with Recipe 4.

## Recipe 2 — Name the topics well

Three levels of naming, cheapest first. Attach via `representation_model`, then the names
appear in `get_topic_info()`.

```python
from bertopic.representation import KeyBERTInspired, MaximalMarginalRelevance

# (a) Free, no network — sharper keywords than raw c-TF-IDF
rep = KeyBERTInspired()

# (b) Diversify keywords so a topic isn't 10 synonyms of one word
rep = MaximalMarginalRelevance(diversity=0.4)

# (c) LLM short labels (needs OPENAI_API_KEY). One call per topic, not per doc.
import openai
from bertopic.representation import OpenAI as BTOpenAI
client = openai.OpenAI()
prompt = ("I have a topic described by these keywords: [KEYWORDS]\n"
          "and these documents: [DOCUMENTS]\n"
          "Give a short (3-5 word) human-readable topic label.")
rep = BTOpenAI(client, model="gpt-4o-mini", chat=True, prompt=prompt,
               nr_docs=4, doc_length=200)

# Pass at construction, OR update an already-fitted model without re-clustering:
topic_model.update_topics(docs, representation_model=rep)
print(topic_model.get_topic_info()[["Topic", "Count", "Name"]].head(20))
```

Anthropic works the same via a compatible client, or roll your own: pull
`topic_model.get_topic(k)` keywords + `get_representative_docs(k)` and prompt Claude yourself
— cheap because it's one prompt per topic, not per document.

## Recipe 3 — Export a usable deliverable

```python
info = topic_model.get_topic_info()
rows = []
for t in info["Topic"]:
    if t == -1:
        continue
    kws = ", ".join(w for w, _ in topic_model.get_topic(t)[:10])
    reps = topic_model.get_representative_docs(t)[:3]
    rows.append({"topic": t,
                 "name": info.loc[info.Topic == t, "Name"].iloc[0],
                 "size": int(info.loc[info.Topic == t, "Count"].iloc[0]),
                 "keywords": kws,
                 "example_1": reps[0] if reps else ""})
pd.DataFrame(rows).sort_values("size", ascending=False).to_csv("topics.csv", index=False)

# Per-document assignment (topic + name + probability if computed)
topic_model.get_document_info(docs).to_parquet("doc_topics.parquet")
```

## Recipe 4 — Control topic count & outliers

```python
# Too many topics? Merge down to a target (rebuilds c-TF-IDF, no re-embed):
topic_model.reduce_topics(docs, nr_topics=30)

# Auto-merge similar topics instead of a fixed number:
topic_model.reduce_topics(docs, nr_topics="auto")

# Reassign the -1 noise bucket into real topics:
new_topics = topic_model.reduce_outliers(docs, topics, strategy="c-tf-idf")
topic_model.update_topics(docs, topics=new_topics)   # refresh names after reassigning
```

## Recipe 5 — Assign NEW documents later (incremental)

Fit once, then classify incoming docs against the frozen topic space. Requires
`prediction_data=True` on HDBSCAN (set in Recipe 1) OR `calculate_probabilities=True`.

```python
topic_model.save("model_dir", serialization="safetensors",
                 save_embedding_model="all-MiniLM-L6-v2")   # portable, no pickle

# ...later / другой process...
tm = BERTopic.load("model_dir")
new_topics, new_probs = tm.transform(["a brand new ticket about refund delays"])
```

`safetensors` avoids pickle security warnings and is far smaller than the default. For a
truly streaming corpus (topics themselves evolve), use `topic_model.partial_fit` with an
online UMAP/cluster backend — see BERTopic's "online topic modeling" guide.

## Recipe 6 — Scale to millions

- **Embed once, cache to disk** (`np.save`) and always pass `embeddings=`. Never re-embed to
  retune clustering — UMAP/HDBSCAN take seconds vs. minutes of embedding.
- `calculate_probabilities=False` (soft probs are O(topics²)).
- Swap the embedder for a lighter/faster one, or precompute with a GPU box, then cluster on
  CPU locally.
- Very large N: raise `UMAP(low_memory=True)` and `min_cluster_size` proportionally
  (~0.1–0.5% of N is a good start).

## Verify
- **Coherence smoke test**: eyeball `get_topic_info()` — the top ~10 topics' keywords should
  each read as a coherent theme, not a bag of stopwords. If they don't, raise `min_df` /
  add `stop_words`, or switch to `KeyBERTInspired`.
- **Outlier share**: `(pd.Series(topics) == -1).mean()` should be < ~0.4. Higher → lower
  `min_cluster_size` or run `reduce_outliers`.
- **Stability**: re-run with the same `random_state` — topic sizes should match. If they
  wander, you forgot to pin UMAP `random_state` or you re-embedded.
- **Round-trip**: `BERTopic.load(...).transform(docs[:5])` returns the same topics the fit
  assigned.

## Pitfalls
- **UMAP is stochastic** — no `random_state` means non-reproducible topics run to run. Always
  pin it.
- **`min_topic_size` vs `min_cluster_size`**: BERTopic's own `min_topic_size` is ignored once
  you pass a custom `hdbscan_model`; then it's HDBSCAN's `min_cluster_size` that governs.
- **Topic `-1` is not a topic** — it's noise. Filter it out of any counts, charts, or "top
  themes" summaries or you'll report garbage as the biggest cluster.
- **Short/near-identical docs** collapse into giant blobs. Dedup first
  (corpus-dedup-pipeline) and consider dropping < 3-word rows.
- **Non-English / mixed language**: default MiniLM is English-centric. Use
  `paraphrase-multilingual-MiniLM-L12-v2` for multilingual corpora.
- **Don't feed the LLM every document** for naming — it's one prompt per topic. Feeding all
  docs is slow and costs a fortune.
- **`fit_transform` on <200 docs** is unstable; below that, prompt an LLM to theme the raw
  text directly instead of clustering.
- **Pickle `.save()`** (the default) is version-fragile and flagged by scanners — prefer
  `serialization="safetensors"`.
