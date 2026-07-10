---
name: magika-file-triage
category: data-analysis
description: >
  Detect the TRUE content type of huge, mislabeled, or extensionless file
  collections and route each file to the right parser using Google Magika (a
  deep-learning detector, ~5ms/file, 200+ types, no libmagic needed) with a
  native `file` fallback. Reach for this when extensions lie, when a scraper or
  export dumps thousands of unknown blobs, before feeding a pipeline that
  assumes format, or when you must split code / docs / images / archives from a
  mixed dump. Emits JSONL (path, label, mime, group, score) you can branch on.
when_to_use:
  - You have a directory of files with wrong, missing, or untrusted extensions
  - Before a parser/ETL step that assumes a format and would crash on the wrong one
  - Splitting a mixed dump into code / documents / images / archives / media
  - Quarantining or flagging files whose real type disagrees with their name
  - Building a content index and you need a reliable per-file type column
  - You want confidence scores, not just a guessed MIME string
when_not_to_use:
  - You only need to read one known-format file — just open it (use `pdf`, `xlsx`, `docx` skills)
  - You need deep archive/EXIF/container metadata — use `exiftool` or `bulk-content-extraction`
  - You need to extract text/tables from files — use `bulk-content-extraction` after triage
  - Deduping near-identical files — use `corpus-dedup-pipeline` (hashing, not typing)
keywords:
  - magika
  - file type detection
  - content type
  - mime type
  - libmagic
  - file triage
  - extensionless
  - magic bytes
  - file command
  - routing
  - jsonl
  - unknown files
  - format detection
  - data cleaning
similar_to:
  - corpus-dedup-pipeline
  - bulk-content-extraction
  - incremental-content-index
  - data-quality-validation
inputs_needed: A path (file or directory) to triage, and where to route each type
produces: A JSONL type manifest (path, label, mime, group, score, engine) plus a routing recipe
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Magika File Triage

Identify what a file *actually is* — not what its extension claims — and route
it to the correct downstream parser. Google Magika is a small ONNX model that
classifies 200+ content types from the first bytes in ~5ms, with real
confidence scores. It is pure-Python (no libmagic, no `brew` needed), which
matters on this Mac. The native `file` binary is the zero-install fallback.

## When to use

Use it the moment you can't trust `.ext`: scraper dumps, S3 exports, forensic
piles, user uploads, or any "folder of 40k mystery blobs" before a pipeline
that assumes format. `file` calls a shell script a `text/plain`; Magika calls
it `shell`. That difference is why this skill exists.

## Prerequisites

- **Magika (preferred):** `pip install magika` — pulls `onnxruntime`
  (~40MB wheel), CPU-only, works on Python 3.9 (this Mac). No libmagic.
- **Fallback (zero-install):** the native `file` binary ships with macOS
  (`/usr/bin/file`, present here) and Linux. The helper auto-detects and uses
  it if Magika is missing — so the skill *always runs*, just with coarser MIME.
- Avoid `python-magic`: it needs libmagic via `brew install libmagic`, which is
  unavailable on this Mac. Use native `file` instead — same source, no install.

## Recipes

### 1. One-line CLI triage (Magika installed)

```bash
# Recursive, JSONL, with score — one record per file
magika -r --jsonl -s ./mystery_dump/ > triage.jsonl

# Human-readable spot check
magika ./mystery_dump/*        # e.g. "code.txt: Shell script (code)"
magika -l ./x                  # bare label only:  shell
magika -i ./x                  # MIME only:         text/x-shellscript
cat blob | magika -            # classify stdin
```

Key flags: `-r` recursive, `--jsonl`/`--json` machine output, `-s` score,
`-l` label-only, `-i` mime, `--no-dereference` don't follow symlinks.

### 2. Batch triage helper (Magika API + auto-fallback)

`scripts/triage.py` emits one JSONL record per file and degrades to the `file`
binary when Magika isn't installed. It never renames or moves user files.

```bash
python3 scripts/triage.py ./mystery_dump/ > triage.jsonl
# {"path":".../x","label":"javascript","mime":"application/javascript",
#  "group":"code","score":0.9998,"engine":"magika","low_confidence":false}
```

Records below score `0.90` are marked `"low_confidence": true` for review.

### 3. Python API — classify and branch in code

```python
from magika import Magika
m = Magika()

res = m.identify_path("./blob")          # or identify_bytes(b"..."), identify_stream(f)
o = res.output
print(o.label, o.mime_type, o.group, o.is_text, res.score)
#     javascript  application/javascript  code  True  0.9998

# Batch (fast): one model call amortized over the list
results = m.identify_paths([p1, p2, p3])
```

Result fields: `output.label` (unique type id), `output.mime_type`,
`output.group` (`code`/`document`/`image`/`archive`/`audio`/`video`/`text`…),
`output.description`, `output.extensions`, `output.is_text`, `res.score`.

### 4. Route each type to the right parser

Branch on `group` (coarse) or `label` (precise). Example fan-out from the JSONL:

```bash
# Move nothing; just build per-type worklists for downstream skills
jq -r 'select(.group=="document") | .path' triage.jsonl > docs.txt   # -> pdf/docx/xlsx
jq -r 'select(.group=="image")    | .path' triage.jsonl > imgs.txt   # -> perceptual-image-dedup
jq -r 'select(.group=="code")     | .path' triage.jsonl > code.txt
jq -r 'select(.low_confidence)    | .path' triage.jsonl > review.txt  # human check
```

Then hand `docs.txt` to `bulk-content-extraction`, `imgs.txt` to an image
skill, etc. Triage decides *which* parser; it does not parse.

### 5. Find liars — real type disagrees with the extension

```bash
python3 scripts/triage.py ./dump > t.jsonl
jq -r 'select((.path|ascii_downcase|endswith("."+.label))|not)
       | [.path,.label,.mime]|@tsv' t.jsonl | head
# Surfaces the renamed .jpg that is really a zip, the .txt that is really JSON.
```

## Verify

- Syntax/smoke the helper without any install:
  `python3 -c "import ast; ast.parse(open('scripts/triage.py').read())"`
  then run it on two known files and confirm the JSONL labels/MIME are right
  (the `file` fallback already yields correct `application/pdf`, `text/plain`).
- With Magika installed, confirm `magika --version` prints and a `.txt`
  containing JS classifies as `javascript` (score > 0.9), proving the model —
  not the extension — drove the call.
- Sanity-check `review.txt`/low-confidence rows by eye before routing.

## Pitfalls

- **Extensions are ground-truth to nobody.** Never route on `.ext`; route on
  Magika's `label`/`group`. That is the whole point.
- **libmagic dead-end on this Mac.** `python-magic` import will fail without
  `brew install libmagic`. Use Magika (pure ONNX) or native `file`; the helper
  already picks a working engine.
- **Empty/tiny files** get low scores and may fall to `txt`/`empty` — filter
  `low_confidence` and treat zero-byte files as a special case.
- **Symlinks & huge trees:** the helper skips symlinks; for millions of files
  prefer the Rust CLI (`magika -r --jsonl`) which is faster than per-call Python.
- **Magika predicts *content*, not container internals.** A `.docx` reads as a
  `zip`-family/office type by bytes; use `group=="document"` + extension hints
  for Office formats, then let the `docx`/`xlsx` skills confirm.
- **Immutability:** triage is read-only. If you must reorganize by type, copy
  into new type-named dirs — never mutate the source dump in place.

## Source

Grounded against `google/magika` (Apache-2.0) `python/README.md` API/CLI and
`ahupp/python-magic` docs, verified 2026-07-09. Helper authored fresh.
