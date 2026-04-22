# Documents

**Create, parse, and edit real document formats.**

These skills handle .docx, .pdf, .pptx, .xlsx natively — meaning the output is a real Word / Excel / PowerPoint / PDF file, not a Markdown approximation.

## Index

| Skill | File types | Use for |
|---|---|---|
| [`docx`](docx) | .docx | Create/read/edit Word docs. TOC, headings, page numbers, letterheads, find/replace, tracked changes, inserting images. |
| [`pdf`](pdf) | .pdf | Create, merge, split, rotate, watermark, form-fill, encrypt, extract text/images, OCR scanned PDFs. |
| [`pptx`](pptx) | .pptx | Create decks, parse slides, edit templates/layouts, speaker notes, comments. |
| [`xlsx`](xlsx) | .xlsx / .xlsm / .csv / .tsv | Create, edit, clean, compute, chart, convert tabular files. |
| [`doc-coauthoring`](doc-coauthoring) | Any text | Structured workflow for writing docs/specs/proposals — context transfer, iterative refinement, reader-verification. |
| [`internal-comms`](internal-comms) | Any text | Status reports, leadership updates, 3P updates, newsletters, FAQs, incident reports, project updates. |

## When each triggers

The binary-format skills (`docx`/`pdf`/`pptx`/`xlsx`) trigger as soon as a file of that extension is mentioned — input, output, or both.

**Don't use** these for:
- Google Docs / Sheets (use the relevant API)
- Markdown / HTML reports (use `frontend-design` or `canvas-design`)
- Printing Python dataframes to console (use pandas directly)

## Pair with

- [`../frontend-and-design/theme-factory`](../frontend-and-design/theme-factory) — cohesive theming for decks and docs
- [`../frontend-and-design/brand-guidelines`](../frontend-and-design/brand-guidelines) — Anthropic brand for decks/docs
- [`../frontend-and-design/canvas-design`](../frontend-and-design/canvas-design) — cover art / poster pages inside docs

## Attribution

All skills originate from [`anthropics/skills`](https://github.com/anthropics/skills).
