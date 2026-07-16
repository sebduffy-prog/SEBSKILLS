---
name: bulk-content-extraction
category: data-analysis
description: >
  Extract clean text plus structured metadata from thousands of heterogeneous files
  (PDF, DOCX, PPTX, XLSX, HTML, EML, EPUB, RTF, ODT, images) into one normalized JSONL
  corpus, using Apache Tika (1000+ formats, one JVM server, dep-free HTTP client) or
  unstructured.io (element-typed, chunk-ready Python). Reach for this to turn a messy
  document dump into indexable rows before RAG, embedding, dedup, search, or analysis;
  to run OCR over scanned PDFs/images at scale; and to keep parsing resilient so one bad
  file never kills the batch. Emits per-file path/mime/chars/meta/text you branch on.
when_to_use:
  - You have hundreds or thousands of mixed-format documents and need one uniform text+metadata corpus
  - Preparing raw documents for RAG chunking, embeddings, search indexing, or LLM fine-tuning
  - You need format-agnostic extraction across PDF/Office/HTML/email/ebook without one library per type
  - Running OCR over scanned PDFs and images at batch scale
  - You want element structure (titles, tables, lists, page numbers) not just a flat text blob
  - A one-off pipeline must survive corrupt/encrypted/oversized files without crashing
when_not_to_use:
  - You need to detect the TRUE type of extensionless/mislabeled blobs first — run magika-file-triage, then this
  - You only need one known file read/edited — use the pdf, docx, xlsx, or pptx skills directly
  - The source is live web pages, not files on disk — use firecrawl-scrape or structured-page-extraction
  - You already have clean text and want near-duplicates removed — use corpus-dedup-pipeline
  - You want to keep an index fresh as files change over time — use incremental-content-index
keywords:
  - text extraction
  - apache tika
  - unstructured.io
  - document parsing
  - metadata extraction
  - ocr
  - pdf extraction
  - rmeta
  - jsonl corpus
  - rag ingestion
  - office documents
  - content pipeline
  - tesseract
  - partition
  - batch extraction
similar_to:
  - magika-file-triage
  - corpus-dedup-pipeline
  - incremental-content-index
  - structured-page-extraction
  - data-quality-validation
inputs_needed: >
  Path/glob to the document tree and rough file count; which formats dominate; whether
  scanned PDFs/images need OCR; whether flat text or element structure (tables/titles) is
  needed downstream; a cap on per-file text length; and where to write the JSONL corpus.
produces: One JSONL corpus (one row per file — path, mime, chars, selected metadata, extracted text) plus a stderr ok/fail tally.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Bulk Content Extraction

Turn a directory of heterogeneous documents into one clean, normalized JSONL corpus.
Two engines cover almost everything:

- **Apache Tika** — one Java server, 1000+ formats, the widest coverage and most
  battle-tested metadata. Best for "throw anything at it" dumps. Client is dep-free HTTP.
- **unstructured.io** — pure Python, returns typed *elements* (Title, NarrativeText,
  Table, ListItem) with page numbers. Best when downstream RAG wants structure/chunking.

Pick Tika for breadth and metadata; pick unstructured for structure. You can run both.

## When to use

Use this after (optionally) `magika-file-triage` has confirmed real file types, when you
need a single uniform corpus from many formats. See `when_not_to_use` for single-file or
web-page cases that have a better dedicated skill.

## Prerequisites

Honest deps — neither is trivial, so choose one:

**Tika path** (recommended for scale, minimal Python deps):
- Java 11+ on PATH (`java -version`). macOS without brew: install Temurin from adoptium.net.
- The Tika server jar (~90 MB). Grab the latest `tika-server-standard`:
  ```bash
  curl -fL -o tika-server.jar \
    "https://dlcdn.apache.org/tika/3.2.1/tika-server-standard-3.2.1.jar"
  # (check https://tika.apache.org/download.html for the current version)
  ```
- For OCR/images, Tika calls Tesseract if `tesseract` is on PATH; otherwise images yield
  metadata only. The dep-free client in `scripts/tika_extract.py` needs **no pip installs**.

**unstructured path** (Python-native, structure-aware):
```bash
pip install "unstructured[all-docs]"   # or narrow: "unstructured[pdf,docx,pptx]"
```
System libs it shells out to: `poppler-utils` (PDF), `tesseract-ocr` (OCR),
`libmagic` (type sniffing), `libreoffice` (legacy Office). On a bare macOS these are the
hard part — prefer the Tika path if you cannot install them.

## Recipe A — Tika server + dep-free bulk client (widest coverage)

1. Start the server (leave it running in another terminal / background):
   ```bash
   java -jar tika-server.jar --port 9998
   # health check:
   curl -s http://localhost:9998/version
   ```
2. Sanity-check one file end to end — `/rmeta/text` returns a JSON array whose first
   element is the container doc; text lives under the `X-TIKA:content` key:
   ```bash
   curl -s -T sample.pdf http://localhost:9998/rmeta/text | python3 -m json.tool | head
   ```
3. Extract the whole tree to JSONL with the bundled client (no pip deps):
   ```bash
   python3 scripts/tika_extract.py /path/to/docs \
     --server http://localhost:9998 \
     --out corpus.jsonl \
     --ext .pdf,.docx,.pptx,.html \   # omit --ext to take everything
     --write-limit 0 \                # cap chars/file if RAM matters
     --skip-existing                  # resumable: re-run to fill gaps
   ```
   Each row: `{path, mime, chars, meta{...}, text}` or `{path, error}` on failure —
   one bad file is logged, never fatal. Final stderr line: `ok=… fail=… skipped=…`.

Raw curl endpoints if you skip the script: `PUT /tika` (XHTML), `PUT /tika/text`
(plain text), `PUT /rmeta/text` (recursive metadata+text as JSON), `PUT /meta` (metadata
only). Add `--header "writeLimit: 100000"` to bound per-file text.

## Recipe B — unstructured.io (typed elements for RAG)

```python
from unstructured.partition.auto import partition
from unstructured.staging.base import elements_to_json
import glob, json, os

with open("corpus.jsonl", "w", encoding="utf-8") as out:
    for fp in glob.glob("docs/**/*", recursive=True):
        if not os.path.isfile(fp):
            continue
        try:
            # strategy="hi_res" forces OCR/layout on scanned PDFs; "fast" is text-only.
            els = partition(filename=fp, strategy="fast")
            text = "\n\n".join(str(e) for e in els)
            rec = {
                "path": fp,
                "n_elements": len(els),
                "types": sorted({type(e).__name__ for e in els}),
                "chars": len(text),
                "text": text,
            }
        except Exception as e:                     # keep the batch alive
            rec = {"path": fp, "error": f"{type(e).__name__}: {e}"}
        out.write(json.dumps(rec, ensure_ascii=False) + "\n")
```
`partition()` auto-dispatches by type. For chunk-ready RAG output use
`from unstructured.chunking.title import chunk_by_title` on the element list.

## Verify

```bash
# rows written, and how many failed
wc -l corpus.jsonl
python3 - <<'PY'
import json
ok=err=empty=0
for line in open("corpus.jsonl"):
    r=json.loads(line)
    if r.get("error"): err+=1
    elif not r.get("chars"): empty+=1
    else: ok+=1
print(f"ok={ok} empty_text={empty} errored={err}")
PY
```
Spot-check: text is real prose (not gibberish/encoding mojibake), `mime` matches the
extension, and scanned PDFs have non-zero `chars` only if OCR actually ran. Empty text on
image-heavy PDFs = OCR is not wired up (see Pitfalls).

## Pitfalls

- **Scanned PDFs/images come back empty.** Tika/unstructured only OCR when Tesseract is
  installed and on PATH; Tika additionally needs `tesseract` reachable by the JVM. No
  Tesseract → images/scans give metadata but no text. Verify with `tesseract --version`.
- **`X-TIKA:content` vs `content`.** The `/rmeta` endpoint nests text under
  `X-TIKA:content` inside each metadata object (the script handles this); the older
  `tika` *python package* (`from tika import parser`) returns a flat `{"content","metadata"}`
  dict instead. Do not mix the two shapes.
- **Java missing / wrong version.** Tika server needs Java 11+. `java -version` failing is
  the #1 cause of "connection refused" to :9998 — the server never started.
- **`writeLimit` silently truncates.** A per-file char cap protects RAM but drops the tail
  of long docs with no error. Leave it at 0 unless you hit memory pressure.
- **Encrypted / password-protected files** return an error row, not text — filter them out
  or supply passwords via Tika config; never let them look like "extracted but empty".
- **unstructured's system deps are the real work.** `pip install` succeeds but PDFs still
  fail without `poppler`/`tesseract`. On locked-down macOS, the Tika server jar is the
  lower-friction route.
- **Triage first for messy dumps.** Wrong/missing extensions mislead the `--ext` filter and
  waste parser time — run `magika-file-triage` first, then feed real types here.
- **De-dup after, not during.** This skill extracts; near-identical docs still slip through.
  Pipe `corpus.jsonl` into `corpus-dedup-pipeline` before indexing.
