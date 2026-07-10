---
name: embedding-model-training
category: ml
description: >-
  Fine-tune embedding (bi-encoder) and reranker (cross-encoder) models with
  Sentence Transformers v3/v4 — pick the right loss for your data shape, mine
  hard negatives, wire an evaluator, and train via the Trainer API. Also covers
  SetFit few-shot text classification (8-64 labels/class, no GPU cluster).
  Use when building semantic search, RAG retrieval, dedup, or text classifiers.
when_to_use:
  - Fine-tuning a bi-encoder for retrieval/RAG so domain queries match domain docs
  - Training a cross-encoder reranker to re-score a first-stage retriever's top-k
  - You have (anchor, positive) or (query, doc, label) pairs and must pick a loss
  - Retrieval recall is poor and you need hard-negative mining to sharpen the model
  - Few-shot text classification with tens of labelled examples per class (SetFit)
when_not_to_use:
  - Using an off-the-shelf embedding model unchanged — just call SentenceTransformer.encode
  - Full LLM/decoder LoRA fine-tuning — use lora-qlora-finetune
  - Measuring an already-trained model's quality end to end — use ml-model-eval
  - Graph-structured node embeddings — use build-train-gnn
keywords:
  - sentence-transformers
  - embeddings
  - bi-encoder
  - cross-encoder
  - reranker
  - hard-negative-mining
  - multiplenegativesrankingloss
  - setfit
  - few-shot
  - semantic-search
  - rag
  - contrastive-loss
  - matryoshka
  - triplet-loss
similar_to:
  - build-train-gnn
  - neural-net-from-scratch
  - lora-qlora-finetune
  - ml-model-eval
inputs_needed: >-
  Labelled text pairs/triplets (anchor+positive, query+doc+score, or
  sentence+class); a base checkpoint (e.g. all-MiniLM-L6-v2); GPU recommended
  but small runs work on CPU/MPS.
produces: >-
  A fine-tuned SentenceTransformer / CrossEncoder / SetFit model directory
  (config + weights) plus evaluator metrics, ready to load with
  from_pretrained and encode/predict.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Embedding & Reranker Model Training

Fine-tune retrieval models with the Sentence Transformers **Trainer** API (v3+,
mirrors Hugging Face `transformers`). Two families: **bi-encoder**
(`SentenceTransformer`) encodes each text to a vector independently — fast,
first-stage retrieval / RAG. **Cross-encoder** (`CrossEncoder`) scores a
`(query, doc)` pair jointly — slower, sharper, used to **rerank** the top-k.
Plus **SetFit** for few-shot classification from a handful of labels.

## When to use

When a generic model mismatches your domain (legal, medical, code, SKUs) and you
have — or can synthesize — labelled pairs. If recall is already good off-the-shelf,
skip training and just `encode`.

## Prerequisites

- Python 3.9+. Install: `pip install "sentence-transformers>=3.0" datasets accelerate`
  (add `pip install setfit` only for the SetFit recipe).
- A base checkpoint. Good starting points: `sentence-transformers/all-MiniLM-L6-v2`
  (fast, 384-dim), `BAAI/bge-base-en-v1.5`, or `google-bert/bert-base-uncased`
  (train from scratch).
- GPU strongly recommended. On this Mac, MPS works for tiny runs: pass no CUDA
  flags, set `fp16=False`, `bf16=False`. Don't expect speed.
- The **golden rule of the Trainer**: columns that are *not* named `label`,
  `labels`, `score`, or `scores` are treated as model **inputs**, and their
  **order** must match what the loss expects. Names are cosmetic; order is law.

## Recipe 1 — Bi-encoder for retrieval (in-batch negatives)

`MultipleNegativesRankingLoss` (MNRL) is the default workhorse: it needs only
`(anchor, positive)` pairs and treats every *other* positive in the batch as a
negative. Bigger batches = more negatives = better. Use
`BatchSamplers.NO_DUPLICATES` so a batch never contains two identical texts.

```python
from datasets import load_dataset, Dataset
from sentence_transformers import (
    SentenceTransformer,
    SentenceTransformerTrainer,
    SentenceTransformerTrainingArguments,
)
from sentence_transformers.losses import MultipleNegativesRankingLoss
from sentence_transformers.training_args import BatchSamplers
from sentence_transformers.evaluation import InformationRetrievalEvaluator

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Column ORDER = loss inputs: input0=anchor, input1=positive. No label column.
train_dataset = Dataset.from_dict({
    "anchor":   ["how do I reset my password", "cancel my subscription"],
    "positive": ["Password reset: go to Settings > Security > Reset.",
                 "To cancel, open Billing and click End Plan."],
})

loss = MultipleNegativesRankingLoss(model)

args = SentenceTransformerTrainingArguments(
    output_dir="models/miniLM-retrieval",
    num_train_epochs=1,
    per_device_train_batch_size=64,          # push this as high as VRAM allows
    learning_rate=2e-5,
    warmup_ratio=0.1,
    fp16=True,                               # bf16=True on Ampere+; both False on CPU/MPS
    batch_sampler=BatchSamplers.NO_DUPLICATES,
    eval_strategy="steps", eval_steps=200,
    save_strategy="steps", save_steps=200, save_total_limit=2,
    logging_steps=50,
)

trainer = SentenceTransformerTrainer(
    model=model, args=args,
    train_dataset=train_dataset,
    loss=loss,
)
trainer.train()
model.save_pretrained("models/miniLM-retrieval/final")
```

**If you also have known negatives**, use triplets `(anchor, positive, negative)`
with the same MNRL — it uses the explicit negative *and* in-batch ones. Or add a
`negative` column; three input columns, still no label.

**Matryoshka** (truncatable vectors — store 768, search at 128): wrap the loss so
accuracy survives slicing:
```python
from sentence_transformers.losses import MatryoshkaLoss
loss = MatryoshkaLoss(model, MultipleNegativesRankingLoss(model),
                      matryoshka_dims=[768, 512, 256, 128, 64])
```

## Recipe 2 — Mine hard negatives, then train a reranker

Random negatives are too easy. `mine_hard_negatives` uses an existing embedding
model to find *near-misses* — docs that look relevant but aren't — which force
the model to learn fine distinctions.

```python
from sentence_transformers.util import mine_hard_negatives

# `dataset` has columns: {"query", "answer"} (positive pairs)
hard = mine_hard_negatives(
    dataset,
    model,                       # embedder used to find look-alikes
    num_negatives=5,
    range_min=10,                # skip the top-10 (likely true positives / dupes)
    range_max=50,                # search within top-50 candidates
    max_score=0.8,               # reject candidates too similar to the query
    margin=0.1,                  # negative must be >=0.1 less similar than the positive
    sampling_strategy="top",     # "top" = hardest; "random" = varied
    output_format="labeled-pair",# (query, doc, label∈{0,1}) — for cross-encoder BCE
    batch_size=512,
)
```

`output_format` shapes the result for the loss you'll use next:
- `"labeled-pair"` → `(query, doc, label)` for a **cross-encoder** BCE loss.
- `"triplet"` → `(anchor, positive, negative)` for bi-encoder MNRL/TripletLoss.
- `"n-tuple"` → one positive + N negatives per row.

**Train the cross-encoder reranker** on the mined labelled pairs:

```python
from sentence_transformers import CrossEncoder
from sentence_transformers.cross_encoder import (
    CrossEncoderTrainer, CrossEncoderTrainingArguments,
)
from sentence_transformers.cross_encoder.losses import BinaryCrossEntropyLoss

model = CrossEncoder("google-bert/bert-base-uncased", num_labels=1)  # 1 = relevance score
loss = BinaryCrossEntropyLoss(model)

args = CrossEncoderTrainingArguments(
    output_dir="models/reranker",
    num_train_epochs=1,
    per_device_train_batch_size=32,
    learning_rate=2e-5, warmup_ratio=0.1, fp16=True,
    eval_strategy="steps", eval_steps=200, save_steps=200,
)
trainer = CrossEncoderTrainer(model=model, args=args,
                              train_dataset=hard, loss=loss)
trainer.train()

# Inference: rank candidate docs for a query
scores = model.predict([("reset password", d) for d in candidate_docs])
```

## Recipe 3 — Similarity regression (labelled scores)

When you have graded similarity (e.g. STS, 0.0–1.0), use a score-based loss.
`CoSENTLoss` generally beats the older `CosineSimilarityLoss`.

```python
from sentence_transformers.losses import CoSENTLoss
# dataset columns: {"sentence1", "sentence2", "score"}  (score is float 0-1)
loss = CoSENTLoss(model)
```

Evaluate with `EmbeddingSimilarityEvaluator(sentences1, sentences2, scores)`.

## Recipe 4 — SetFit few-shot classification

No pairs, no GPU cluster — just ~8–64 labelled examples per class. SetFit
contrastively fine-tunes a sentence encoder then fits a lightweight head.

```python
from datasets import load_dataset
from setfit import SetFitModel, Trainer, TrainingArguments, sample_dataset

ds = load_dataset("sst2")
train = sample_dataset(ds["train"], label_column="label", num_samples=8)  # 8/class

model = SetFitModel.from_pretrained("sentence-transformers/paraphrase-mpnet-base-v2")
args = TrainingArguments(batch_size=16, num_epochs=1)
trainer = Trainer(model=model, args=args,
                  train_dataset=train, eval_dataset=ds["validation"],
                  metric="accuracy")
trainer.train()
print(trainer.evaluate())                 # -> {"accuracy": ...}
model.save_pretrained("models/setfit-sst2")
preds = model.predict(["what a fantastic film", "utter waste of time"])
```

## Choosing a loss (cheat sheet)

| Data you have | Loss | Input columns | Label |
|---|---|---|---|
| `(anchor, positive)` pairs | `MultipleNegativesRankingLoss` | 2+ | none |
| `(anchor, pos, neg)` triplets | `MultipleNegativesRankingLoss` / `TripletLoss` | 3 | none |
| graded similarity 0–1 | `CoSENTLoss` (or `AnglELoss`) | 2 | `score` |
| binary duplicate/not | `ContrastiveLoss` / `OnlineContrastiveLoss` | 2 | `label` 0/1 |
| class labels, NLI-style | `SoftmaxLoss` | 2+ | `label` int |
| truncatable vectors | wrap any of the above in `MatryoshkaLoss` | — | — |
| cross-encoder rerank | `BinaryCrossEntropyLoss` | 2 | `label` float |

Symmetric retrieval (query↔query, e.g. dedup) → `MultipleNegativesSymmetricRankingLoss`.

## Verify

- **Smoke test the pipeline** on 50 rows / 1 epoch before a full run — confirms
  column order and loss/dataset compatibility without burning GPU hours.
- **Attach an evaluator** and watch the metric *rise* across steps. For retrieval,
  `InformationRetrievalEvaluator` reports `cosine_ndcg@10` / `cosine_recall@k` on
  a held-out `{corpus, queries, relevant_docs}` set — the number you actually care
  about, not train loss.
- **Reload and encode** to prove the artifact is usable:
  ```python
  m = SentenceTransformer("models/miniLM-retrieval/final")
  from sentence_transformers.util import cos_sim
  q, d = m.encode(["reset password"]), m.encode(["Password reset steps..."])
  print(float(cos_sim(q, d)))   # positive pair should score notably higher than a random pair
  ```
- Compare fine-tuned vs. base evaluator scores on the same eval set — if it didn't
  move, your data or loss is wrong, not your hyperparameters.

## Pitfalls

- **Column order, not names.** `select_columns([...])` / `remove_columns([...])`
  to fix ordering and drop stray columns (an unexpected `id` column becomes a
  phantom text input and silently wrecks training).
- **MNRL wants big batches.** With batch size 8 you get 7 negatives; with 128 you
  get 127. If VRAM limits you, enable `CachedMultipleNegativesRankingLoss` for
  large effective batches, or add explicit mined hard negatives.
- **Duplicates poison in-batch negatives.** Always set
  `batch_sampler=BatchSamplers.NO_DUPLICATES` with MNRL — a repeated positive
  becomes a false negative.
- **Precision flags:** `fp16=True` on most CUDA GPUs, `bf16=True` on Ampere+.
  Set **both False** on CPU/MPS or training NaNs out.
- **Cross-encoder `num_labels=1`** for ranking (regressed score). `num_labels=2`
  gives a 2-class classifier — different head, different `predict` output.
- **Don't eval a reranker with retrieval recall.** Cross-encoders can't retrieve
  (they need candidate pairs); rerank a bi-encoder's top-k and measure the reranked
  order (nDCG/MRR).
- **SetFit ≠ Trainer API.** It has its own `Trainer`/`TrainingArguments` from the
  `setfit` package — don't mix imports with `sentence_transformers`.
- **Overfitting:** 1–3 epochs is enough; more on small sets memorizes.
