---
name: perceptual-image-dedup
category: data-analysis
description: >
  Find exact and near-duplicate images across huge photo/asset libraries. Compute
  perceptual hashes (pHash/dHash) per image, cluster by Hamming distance with faiss
  binary range_search (O(n) not O(n^2)), and — for crops, heavy edits, watermarks or
  recolors that fool pixel hashes — fall back to CLIP embeddings + a faiss L2/cosine
  index. Use to dedup a Downloads/Desktop dump, collapse a stock-photo pile, spot
  reused creative, or clean a training set before ML. Grounded on imagehash + faiss.
when_to_use:
  - Deduping a large folder of photos/screenshots/creative assets before use or archiving
  - Detecting near-duplicates (resizes, re-JPEGs, minor edits) not caught by file hashing
  - Matching crops / watermarked / recolored variants back to an original (CLIP stage)
  - Cleaning a training/eval image set so duplicates don't leak across splits
  - Auditing a stock or DAM library for reused or re-uploaded imagery
when_not_to_use:
  - Deduping arbitrary files by exact bytes only — use sha256/`fdupes`, no perceptual hash needed
  - Text/document dedup — use corpus-dedup-pipeline (MinHash/simhash) instead
  - Reverse image SEARCH against the web — use a hosted API (TinEye/Bing), not local hashing
  - Clustering images by semantic THEME rather than duplication — use embedding-corpus-clustering
keywords: [image dedup, perceptual hash, phash, dhash, imagehash, hamming distance, faiss, near duplicate, clip embeddings, deduplication, binary index, pillow]
similar_to: [corpus-dedup-pipeline, embedding-corpus-clustering, zero-shot-auto-tagging, magika-file-triage]
inputs_needed: Path to the image directory; desired Hamming threshold (default 8/64); whether CLIP crop-matching is needed
produces: JSON clusters of duplicate/near-duplicate file paths (plus optional CLIP match pairs) for review or deletion
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Perceptual Image Dedup

Two complementary stages. Stage 1 (pHash + Hamming) is fast and catches resizes,
recompressions and small edits — run it first, always. Stage 2 (CLIP + faiss) is
heavier but catches crops, big color shifts, watermarks and composited edits that
change pixel layout enough to move the perceptual hash. Add exact-byte hashing as a
zero-cost pre-pass.

## When to use

Reach for this whenever "these images are basically the same" matters: cleaning a
Desktop/Downloads dump, collapsing a stock pile, or stopping duplicate leakage between
ML train/test splits. If you only care about byte-identical files, plain sha256 is
enough — skip the perceptual machinery.

## Prerequisites (honest)

- **Python 3.9+** (macOS system python3 is fine). `Pillow` provides image decoding.
- `pip install imagehash Pillow` — imagehash is BSD-2-Clause (Johannes Buchner).
- **faiss is optional but recommended**: `pip install faiss-cpu`. Without it the helper
  falls back to a brute-force O(n^2) Hamming scan (fine up to a few thousand images).
- **CLIP stage (optional)**: `pip install open_clip_torch torch` OR
  `pip install sentence-transformers`. This pulls torch (large). Only install if Stage 1
  misses crops/edits you care about.
- No brew / no GPU required; everything runs CPU-only. HEIC needs `pip install pillow-heif`.

## Recipes

### 0. Exact-byte pre-pass (free, do first)

```bash
# Group byte-identical files instantly — no decoding, no hashing library.
find /path/to/images -type f \( -iname '*.jpg' -o -iname '*.png' -o -iname '*.webp' \) \
  -exec shasum -a 256 {} + | sort | awk '{c[$1]=c[$1]" "$2} END{for(h in c){n=split(c[h],a," "); if(n>1) print c[h]}}'
```

### 1. pHash near-duplicate clustering (main event)

The bundled `scripts/dedup.py` walks a dir, computes one 64-bit pHash per image, packs
each into 8 bytes, and clusters with faiss `IndexBinaryFlat.range_search` + union-find.

```bash
pip install imagehash Pillow faiss-cpu
python3 scripts/dedup.py /path/to/images --hamming 8 --hash phash --json dups.json
```

- `--hamming N` = max Hamming distance (0–64) to treat as duplicate. **Guide: 0 =
  identical hash, ≤6 = near-identical (resize/recompress), ≤10 = loose (light edits),
  >12 gets noisy.** Start at 8, tune on your data.
- `--hash phash` (DCT-based, robust default) | `dhash` (gradient, fast, edge-sensitive)
  | `average_hash` (weak, cheap) | `whash` (wavelet).
- Output JSON: `{images, duplicate_clusters, duplicated_files, clusters:[[path,...],...]}`
  sorted largest cluster first. Nothing is deleted — you review, then delete.

Minimal inline version if you can't use the script (two images):

```python
import imagehash; from PIL import Image
a = imagehash.phash(Image.open("a.jpg")); b = imagehash.phash(Image.open("b.jpg"))
print(a - b)   # Hamming distance; <=6 => near-duplicate
```

### 2. faiss binary index by hand (for scale / custom flows)

pHash with `hash_size=8` → 64 bits → `np.packbits` → 8 uint8 per image. `d` must be the
**bit** count (64), a multiple of 8.

```python
import numpy as np, faiss, imagehash
from PIL import Image
bits = np.array([imagehash.phash(Image.open(p)).hash.flatten() for p in paths], bool)
vecs = np.packbits(bits, axis=1)                 # (n, 8) uint8
index = faiss.IndexBinaryFlat(vecs.shape[1] * 8) # d = 64 bits
index.add(vecs)
lims, D, I = index.range_search(vecs, 8)         # radius 8 = Hamming threshold
# For >1M images use faiss.index_binary_factory(64, "BHash8x8") (LSH, approximate).
```

`D[j]` is the Hamming distance; walk `lims`/`I` to build clusters (union-find, as in the
script). `range_search` returns all matches within radius — exactly what dedup needs.

### 3. crop_resistant_hash — a middle tier before CLIP

Handles crops/borders better than plain pHash without torch. Note it returns an
`ImageMultiHash`; distance uses `.hash_diff` / subtraction, not a plain int compare:

```python
from imagehash import crop_resistant_hash
from PIL import Image
h1 = crop_resistant_hash(Image.open("full.jpg"))
h2 = crop_resistant_hash(Image.open("cropped.jpg"))
print(h1 - h2)          # lower = more similar; try threshold ~ same 0-64 scale
```

### 4. CLIP + faiss for crops / heavy edits / recolors (heavy stage)

When pHash misses semantically-identical-but-visually-transformed images:

```python
import numpy as np, faiss, torch, open_clip
from PIL import Image
model, _, preprocess = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
model.eval()
def embed(p):
    with torch.no_grad():
        v = model.encode_image(preprocess(Image.open(p).convert("RGB")).unsqueeze(0))
    return torch.nn.functional.normalize(v, dim=-1).cpu().numpy()[0]
X = np.stack([embed(p) for p in paths]).astype("float32")   # unit vectors
index = faiss.IndexFlatIP(X.shape[1])                        # inner product = cosine
index.add(X)
lims, D, I = index.range_search(X, 0.92)                     # cosine >= 0.92 => same content
```

Cosine ≥ ~0.95 = near-certain same image (crop/edit); 0.90–0.95 = likely; below that you
drift into "similar subject", not "duplicate". Tune per library.

## Verify

- `python3 -m py_compile scripts/dedup.py` — must succeed.
- Smoke test with a known pair: copy an image, resize it 90%, run Stage 1 — the two must
  land in one cluster at `--hamming 8`. Then rotate one 90°: pHash will NOT match
  (expected — pHash is not rotation-invariant), proving the threshold isn't just matching
  everything.
- Sanity-check counts: `duplicated_files` should be « `images` on a real library; if it
  balloons, your `--hamming` is too high.
- Spot-open 3 clusters and confirm they are genuinely duplicates before any deletion.

## Pitfalls

- **pHash is NOT rotation/flip invariant.** A 90°/180° rotation, or a mirror, reads as a
  different image. Pre-normalize orientation (respect EXIF `Orientation`, or hash all 4
  rotations) or use the CLIP stage for those.
- **Never delete blind.** Clusters are candidates. Always keep one representative
  (highest resolution / largest file) per cluster and review before `rm`.
- **`hash_size` changes the bit width.** `hash_size=8` → 64 bits → `d=64`. If you raise
  `hash_size`, update the faiss `d` and re-derive your Hamming thresholds — they don't
  transfer across bit widths.
- **faiss binary `d` is bits, not bytes.** Passing 8 (bytes) instead of 64 (bits) silently
  breaks results. And input must be `uint8` from `np.packbits`, not a bool array.
- **Threshold is data-dependent.** Screenshots, flat UI, and near-black frames collapse to
  near-identical hashes and over-merge; photos tolerate higher thresholds. Calibrate on a
  labeled sample, don't ship the default blindly.
- **CLIP over-merges by design.** It matches *content*, so two different photos of the same
  landmark score high. Use it only as a second pass gated behind pHash, and keep the cosine
  cutoff strict (≥0.92) for dedup vs. mere similarity.
- **Decode failures / HEIC.** Corrupt files and `.heic` without `pillow-heif` raise; the
  script skips-and-logs to stderr so one bad file can't abort a 100k-image run.
- **Giant libraries:** `IndexBinaryFlat` is exact but linear per query. Past ~1M images
  switch to `index_binary_factory(64, "BHash8x8")` (approximate LSH) and accept some recall
  loss.
