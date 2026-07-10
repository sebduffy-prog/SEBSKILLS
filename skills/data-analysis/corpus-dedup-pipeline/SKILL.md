---
name: corpus-dedup-pipeline
category: data-analysis
description: >
  Deduplicate large text corpora with a tiered exact -> fuzzy (MinHash/LSH) -> semantic
  (embeddings) pipeline. Use to strip near-duplicate documents before training, RAG
  indexing, or analysis; to pick sane similarity thresholds; to shard millions of docs
  through LSH banding; and to keep exactly one representative per duplicate cluster with
  a full cluster map. Grounded on datasketch MinHashLSH and MinishLab semhash. Reach for
  this whenever "same-ish text appears many times" is hurting a downstream job.
when_to_use:
  - Cleaning a scraped or user-generated corpus before LLM fine-tuning or eval so duplicates do not inflate metrics
  - Removing near-duplicate chunks/documents from a RAG or search index to cut token spend and redundancy
  - Deduplicating millions of records too large for O(n^2) pairwise comparison, needing LSH bucketing
  - Collapsing boilerplate/templated documents (press releases, listings, T&Cs) into one representative each
  - Deciding an exact/fuzzy/semantic threshold and needing to inspect the resulting clusters before deleting anything
when_not_to_use:
  - Deduplicating images or scanned pages -> use perceptual-image-dedup instead
  - Grouping documents by topic rather than by near-identical text -> use embedding-corpus-clustering
  - Deduplicating exact rows in a SQL/Parquet table by key -> use duckdb-analytics or polars-dataframes GROUP BY / distinct
  - Incrementally deduping a growing stream against an existing index -> use incremental-content-index
keywords:
  - deduplication
  - minhash
  - lsh
  - datasketch
  - semhash
  - near-duplicate
  - jaccard
  - shingles
  - embeddings
  - semantic-dedup
  - corpus-cleaning
  - fuzzy-matching
  - clustering
  - text-normalization
similar_to:
  - embedding-corpus-clustering
  - perceptual-image-dedup
  - incremental-content-index
  - bulk-content-extraction
  - data-quality-validation
inputs_needed: >
  Path/glob to the corpus and its format (jsonl/csv/parquet/dir of txt); the text field name;
  rough row count; how aggressive to dedup (exact only, fuzzy, or semantic) and target threshold;
  whether cross-dataset (dedup A against B) or self-dedup; where to write kept records + cluster map.
produces: A deduplicated record set (one representative per cluster) plus a cluster/duplicate map and before/after counts.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Corpus Dedup Pipeline

Tiered deduplication for text: **exact** (cheap, catches copies) -> **fuzzy** (MinHash/LSH, catches
edits/boilerplate) -> **semantic** (embeddings, catches paraphrases). Run only the tiers you need,
cheapest first, and always keep the cluster map so a delete is reversible and auditable.

## When to use

Use when the same-ish document appears many times and it is hurting a downstream job (training
metrics, RAG cost, analysis skew). Skip for image dedup, topic clustering, or plain SQL DISTINCT
(see `when_not_to_use`).

## Prerequisites

- **python3** (3.9+ works for the exact + MinHash tiers).
- **Tier 1/2:** `pip install datasketch` — MIT. Pure-python MinHash + LSH, no native build.
- **Tier 3 (semantic):** `pip install semhash` — MIT (MinishLab). Pulls `model2vec` static embeddings
  (fast, CPU-friendly). **Needs Python 3.10+**; on this Mac's 3.9 use a venv/uv with 3.10+, or stop at Tier 2.
- No brew / no GPU required. Everything below runs CPU-only.
- Decide the unit of dedup first: whole document, or paragraph/chunk. Dedup the same unit you retrieve.

## Recipes

### Tier 1 — Exact dedup (always do this first)

Normalize then hash. Normalization decides what "exact" means — lowercase + collapse whitespace
catches trivially different copies. Keep first occurrence.

```bash
python3 - <<'PY' < corpus.jsonl > kept_exact.jsonl
import sys, json, re, hashlib
seen=set()
def norm(t): return re.sub(r"\s+"," ", t.lower()).strip()
kept=dropped=0
for line in sys.stdin:
    if not line.strip(): continue
    r=json.loads(line)
    h=hashlib.blake2b(norm(r["text"]).encode(), digest_size=16).digest()
    if h in seen: dropped+=1; continue
    seen.add(h); kept+=1; print(json.dumps(r, ensure_ascii=False))
sys.stderr.write(f"exact: kept={kept} dropped={dropped}\n")
PY
```

### Tier 2 — Fuzzy near-dup (MinHash + LSH), scales to millions

Catches edits, added boilerplate, reordered sentences. The helper builds MinHash signatures over
word **shingles** (k-grams), buckets them with `MinHashLSH`, unions candidates with union-find, and
emits one representative per cluster + a cluster map. LSH keeps this near-linear instead of O(n^2).

```bash
python3 scripts/minhash_cluster.py kept_exact.jsonl \
    --threshold 0.8 --num-perm 128 --shingle 3 \
    --clusters clusters.json > kept_fuzzy.jsonl
# stderr -> in=... kept=... removed=...   clusters.json maps root_id -> [member ids]
```

Choosing knobs (datasketch semantics — set at init, immutable):
- `--threshold` = approximate **Jaccard** cutoff. 0.9 = only very close dupes; 0.7 = aggressive; 0.8 is a good default for prose. LSH returns *candidates*; verify exactly if you need a hard guarantee.
- `--num-perm` 128 default. Higher (256) = better accuracy, more RAM/CPU. Lower (64) = faster, coarser.
- `--shingle` word k-gram size. 3 for sentences/prose; 5 for long docs; 1–2 for short titles/tweets.

Raw datasketch, if you want to hand-roll (from the official docs):

```python
from datasketch import MinHash, MinHashLSH
lsh = MinHashLSH(threshold=0.8, num_perm=128)   # threshold & num_perm fixed for life
def sig(shingle_set):
    m = MinHash(num_perm=128)
    for s in shingle_set: m.update(s.encode("utf8"))
    return m
lsh.insert("doc1", sig(a)); lsh.insert("doc2", sig(b))
lsh.query(sig(a))   # -> candidate keys with est. Jaccard > threshold (verify if needed)
```

At tens of millions of rows: use `MinHashLSH(..., storage_config=...)` with a Redis/Cassandra
backend so the index is not in RAM, or shard by a coarse blocking key (domain, date, first-64-chars
hash) and dedup shards in parallel — near-dupes rarely cross a well-chosen block.

### Tier 3 — Semantic dedup (paraphrases), semhash

MinHash misses paraphrases ("cheap flights to Rome" vs "affordable Rome airfare"). semhash embeds
each record (model2vec) and dedups by embedding similarity. Self-dedup one set, or dedup a test set
against train to prevent leakage.

```python
from semhash import SemHash
records = [json.loads(l)["text"] for l in open("kept_fuzzy.jsonl")]

sh = SemHash.from_records(records=records)      # builds embeddings + ANN index
res = sh.self_deduplicate(threshold=0.9)        # cosine-style cutoff; higher = stricter
kept = res.selected                             # deduplicated texts
print(res.duplicate_ratio, res.exact_duplicate_ratio)
for r in res.selected_with_duplicates[:3]:      # audit which dupes collapsed
    print(r)

# Cross-dataset (leakage check): keep only test rows unseen in train
clean_test = SemHash.from_records(records=train).deduplicate(records=test, threshold=0.9).selected
```

`res.selected` = kept, `res.filtered` = removed, `res.duplicate_ratio` = fraction removed.
Start `threshold` high (0.92–0.95) and lower only after eyeballing `selected_with_duplicates`.

## Verify

- **Never delete blind.** Diff counts (`wc -l corpus.jsonl kept_*.jsonl`) and confirm the drop is plausible.
- **Inspect clusters:** open `clusters.json`, pull a few multi-member clusters, read the members — they must genuinely be near-dupes, not false merges. If they are not, raise `--threshold` / `num_perm`.
- **Precision spot-check:** sample 20–30 removed pairs; each should be a real duplicate. Tune threshold up if you see false positives, down if obvious dupes survived.
- **Representative choice:** default keeps the lowest id (earliest). If you want longest/newest as the keeper, sort input accordingly before Tier 2, or post-process `clusters.json`.
- Smoke-test the helper: `python3 -c "import py_compile,sys; py_compile.compile('scripts/minhash_cluster.py',doraise=True)"`.

## Pitfalls

- **Skipping normalization** makes Tier 1 useless — a trailing space or case flip hides an exact copy. Normalize consistently across all tiers.
- **Wrong threshold direction:** MinHash/Jaccard and semhash thresholds both mean "higher = must be more similar to count as dup" — high threshold = fewer removals. Don't invert it.
- **LSH gives candidates, not guarantees.** Near the threshold there are false pos/neg; verify exactly (`MinHash.jaccard`) when a hard cutoff matters.
- **num_perm / threshold are immutable** on a `MinHashLSH` — you cannot retune without rebuilding. Query MinHash objects must share the same `num_perm`.
- **RAM blowup** at scale: 100M signatures in-memory will OOM. Use a storage backend or block-and-shard.
- **Dedup the retrieval unit.** Deduping whole docs but retrieving chunks (or vice-versa) leaves dupes in the index that actually gets queried.
- **semhash needs Python 3.10+** and downloads a model on first run — pre-cache in offline/CI environments; on this Mac's stock 3.9 it will not install, so use a 3.10+ venv or stop at Tier 2.
- **Cross-dataset direction matters:** `SemHash.from_records(train).deduplicate(test)` removes test rows that duplicate train (leakage guard) — not the reverse.
