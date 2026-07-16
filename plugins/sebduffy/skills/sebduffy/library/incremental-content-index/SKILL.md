---
name: incremental-content-index
category: data-analysis
description: >
  Maintain a resumable, content-addressable index over a growing file collection so re-runs
  process ONLY new or changed files, never the whole corpus again. Use to add fast content
  hashing (BLAKE3 / xxh3, size+mtime stat-gate) for change detection, a SQLite manifest as
  source of truth, and a checkpointed usearch ANN index that saves every N adds so an
  interrupted embed/index job resumes where it stopped. Reach for this whenever you re-index a
  directory that keeps growing and full re-scans are wasteful, or a long index build keeps
  dying mid-way and losing progress.
when_to_use:
  - Re-indexing a directory/bucket that grows over time and you must skip files already processed
  - A long embed-then-ANN-index build keeps getting interrupted and you need it to checkpoint and resume
  - Detecting exactly which files are new / changed / deleted since the last run before doing expensive work
  - Building a content-addressable manifest (hash -> file) so identical content is processed once
  - Incrementally adding new documents to an existing vector/search index without a full rebuild
when_not_to_use:
  - One-shot dedup of a static corpus with no re-runs -> use corpus-dedup-pipeline
  - Grouping documents by topic/semantics rather than tracking changes -> use embedding-corpus-clustering
  - Pure SQL/Parquet incremental loads with schema evolution -> use dlt-python-pipelines or duckdb-analytics
  - Watching remote web pages for edits (not local files) -> use web-change-monitor
  - Fast MIME/type triage of unknown files before indexing -> use magika-file-triage
keywords:
  - incremental-index
  - content-addressable
  - blake3
  - xxhash
  - change-detection
  - sqlite-manifest
  - resumable
  - checkpoint
  - usearch
  - ann
  - vector-index
  - idempotent
  - stat-gate
  - corpus
similar_to:
  - corpus-dedup-pipeline
  - embedding-corpus-clustering
  - magika-file-triage
  - bulk-content-extraction
  - web-change-monitor
inputs_needed: >
  The path(s)/glob to the growing collection and file type; where to keep the manifest DB and ANN
  index; what expensive work runs per new/changed file (embed, extract, tag); embedding dim + metric
  if building an ANN index; and how often to checkpoint (batch size).
produces: A SQLite manifest of file->content-hash plus (optionally) a checkpointed usearch ANN index; each re-run emits only NEW/CHANGED/DELETED and processes just those.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Incremental Content Index

Turn "re-scan everything every time" into "process only what actually changed." Three moving parts:

1. **Content hash** (BLAKE3 or xxh3) — a fast fingerprint of file *bytes*, so change detection is
   content-based, not just timestamp-based. A size+mtime `stat()` gate avoids re-hashing untouched files.
2. **SQLite manifest** — the durable source of truth: `path -> size, mtime, content-hash, ann_key`.
   Diffing the manifest against the live filesystem yields NEW / CHANGED / DELETED.
3. **Checkpointed ANN index** (usearch) — the expensive derived artifact. Saved every N adds so a
   killed job resumes from the last checkpoint instead of re-embedding the whole corpus.

The manifest makes the pipeline **idempotent**: run it a hundred times, only genuinely-new bytes get
the expensive treatment.

## When to use

Use when a collection keeps growing and you re-index it repeatedly, or a long index build keeps dying
and losing progress. Skip for one-shot static dedup (`corpus-dedup-pipeline`), topic clustering
(`embedding-corpus-clustering`), or remote-page watching (`web-change-monitor`).

## Prerequisites

- **python3** (3.9 fine). The scanner is stdlib-only and always runs.
- **Faster hashing (optional, recommended):** `pip install blake3` (BLAKE3 is much faster than SHA-2
  and parallel-friendly) or `pip install xxhash` (xxh3). If neither is importable the scanner falls
  back to stdlib `hashlib.blake2b(digest_size=16)` — correct, just slower. **Do not switch algorithms
  mid-manifest**: hashes from different algos are not comparable, so the scanner refuses and tells you
  to rebuild or match. Pick one at the start.
- **ANN index (optional):** `pip install usearch` (Apache-2.0, unum-cloud) + an embedding model of your
  choice (e.g. `sentence-transformers`, `model2vec`, or an API). usearch ships prebuilt wheels; no brew.
- No GPU required. Everything is CPU-friendly and macOS-safe.

Why BLAKE3/xxh3 over an mtime check alone: timestamps lie (touch, restore, clock skew, rsync). Hashing
the bytes is the only reliable "did the content change" signal; the stat-gate is just an optimization
layered on top.

## Recipes

### 1 — Change detection with a resumable manifest (the core loop)

`scripts/scan_manifest.py` walks paths/globs, stat-gates, hashes only when size+mtime moved, diffs the
SQLite manifest, and prints `STATUS<TAB>path` for the statuses you ask for. It commits per batch, so
Ctrl-C mid-scan loses nothing — the next run picks up.

```bash
# First run: everything is NEW
python3 scripts/scan_manifest.py index.db /data/corpus --glob '**/*.txt'
# NEW\t/data/corpus/a.txt ...   (JSON summary to stderr: total/new/changed/deleted)

# Later run after files were added/edited/removed: only the delta prints
python3 scripts/scan_manifest.py index.db /data/corpus --glob '**/*.txt' \
    --emit new,changed,deleted
```

Drive expensive work off the delta — pipe NEW/CHANGED paths straight into your processor:

```bash
python3 scripts/scan_manifest.py index.db /data/corpus --glob '**/*.md' --emit new,changed \
  | while IFS=$'\t' read -r status path; do
        echo "reprocessing $status -> $path"
        # embed "$path" / extract "$path" / tag "$path" ...
    done
```

Flags: `--full-hash` re-hashes every file (use when you suspect in-place edits that preserved
size+mtime); `--batch N` sets the checkpoint/commit size; `--json` prints only the summary (for CI
gates like "fail if >0 changed").

### 2 — Checkpointed usearch ANN index over the delta

Add only NEW/CHANGED vectors to a persistent ANN index and **save every N** so a crash resumes cheaply.
The manifest stores each file's stable integer `ann_key`, so re-embedding a CHANGED file overwrites the
same slot rather than duplicating it.

```python
import sqlite3, numpy as np
from usearch.index import Index

NDIM, CKPT, PATH = 384, 256, "corpus.usearch"     # dim, save cadence, index file
con = sqlite3.connect("index.db")

idx = Index(ndim=NDIM, metric="cos", dtype="f32")
try:
    idx.load(PATH)                                 # resume prior checkpoint if present
except Exception:
    pass

def embed(path):                                   # plug in your model / API here
    ...                                            # -> np.ndarray shape (NDIM,) float32

def next_key(con):
    row = con.execute("SELECT COALESCE(MAX(ann_key),0)+1 FROM files").fetchone()
    return int(row[0])

# `pending` = list of (status, path) from scan_manifest, statuses new+changed
added = 0
for status, path in pending:
    row = con.execute("SELECT ann_key FROM files WHERE path=?", (path,)).fetchone()
    key = row[0] if (row and row[0] is not None) else next_key(con)
    if key in idx:                                 # CHANGED -> replace old vector
        idx.remove(key)
    idx.add(key, embed(path).astype(np.float32))
    con.execute("UPDATE files SET ann_key=? WHERE path=?", (key, path))
    added += 1
    if added % CKPT == 0:                          # checkpoint: durable + resumable
        idx.save(PATH); con.commit()
idx.save(PATH); con.commit()                        # final flush

# Also drop deleted files out of the index (keys the manifest no longer has)
```

Query the finished index:

```python
q = embed("what changed in the pricing policy?").astype(np.float32)
hits = idx.search(q, 10)                            # -> keys + distances (cos: lower = closer)
keys = [m.key for m in hits]
paths = [con.execute("SELECT path FROM files WHERE ann_key=?", (k,)).fetchone()[0] for k in keys]
```

`Index(ndim, metric='cos'|'l2sq'|'ip', dtype='f32'|'f16'|'i8'|'b1')`; `idx.add(key, vec)`,
`idx.search(vec, k)`, `key in idx`, `idx.remove(key)`, `len(idx)`, `idx.save/load(path)`,
`Index.restore(path, view=True)` to memory-map a large index read-only. Shard by writing one
`.usearch` per bucket (date, source) and searching each — keeps any single file rebuildable.

### 3 — Content-addressable dedup as a side effect

Because the manifest already stores the content hash, identical bytes under different paths share a hash
— process the content once, alias the paths:

```sql
-- files with duplicate content (same bytes, different path)
SELECT chash, COUNT(*) n, GROUP_CONCAT(path, ' | ')
FROM files GROUP BY chash HAVING n > 1 ORDER BY n DESC;
```

Embed/extract per distinct `chash`, then map every path with that hash to the same `ann_key`.

## Verify

- **Smoke-test the scanner:** `python3 -c "import py_compile; py_compile.compile('scripts/scan_manifest.py', doraise=True)"`.
- **Idempotency:** run the scan twice with no filesystem change — the second run must report
  `new=0, changed=0` (all `unchanged`). If it re-flags files, an mtime is unstable; use `--full-hash`.
- **Delta correctness:** add one file, edit one, delete one; the next run must emit exactly one NEW, one
  CHANGED, one DELETED (this skill's helper was tested against exactly that scenario).
- **Resumability:** kill the ANN build mid-way, restart — `len(idx)` should already reflect the
  pre-crash checkpoint and only remaining files get embedded. Confirm `len(idx)` == distinct indexed keys.
- **No orphans:** every `ann_key` in the manifest exists in the index, and every index key maps back to a
  live path. Reconcile after DELETED files are removed.

## Pitfalls

- **Switching hash algorithms mid-manifest** silently breaks change detection (blake3 vs blake2b digests
  differ for the same bytes). The helper guards this and aborts; pick one algorithm up front.
- **Trusting mtime alone.** The stat-gate is an optimization, not truth — restores/rsync/editors can
  change bytes while preserving size+mtime (rare) or bump mtime with no content change (common). Content
  hashing is what makes it correct; use `--full-hash` when you must be certain.
- **Not checkpointing the ANN index** — a 6-hour embed job killed at hour 5 with no `idx.save()` starts
  over from zero. Save every N adds and commit the manifest in the same beat so they stay consistent.
- **Duplicating vectors on CHANGED files.** Always `remove(key)` before re-`add(key, ...)`, or reuse the
  stored `ann_key` — otherwise edited files accumulate stale duplicate vectors that pollute search.
- **Forgetting DELETED files** leaves dead vectors in the index returning hits to files that no longer
  exist. Prune keys for paths the manifest dropped.
- **`ndim` mismatch:** the `Index` dim must equal your embedding size exactly, and every added vector must
  match — usearch rejects a wrong-width vector. Fix the model before backfilling.
- **Manifest and index drifting apart** after a partial crash. On startup, treat the manifest as source of
  truth and reconcile: any `ann_key` not in `idx` needs re-adding; any index key with no manifest row is stale.
- **Huge directories in one glob** hold everything in one Python process — shard by subtree and run the
  scanner per shard (each writes to its own manifest, or the same DB via WAL) to bound memory.
