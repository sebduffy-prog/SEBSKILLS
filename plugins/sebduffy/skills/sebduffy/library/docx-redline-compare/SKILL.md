---
name: docx-redline-compare
category: documents
description: >
  Generate a Word tracked-changes redline (native w:ins / w:del markup) between
  two .docx versions so reviewers see exactly what changed and can Accept/Reject
  each edit. Use for comparing draft-vs-final contracts, decks, statements of work,
  policy docs, or any Word file where "what changed since the last version?" needs
  a real markup document — not a plain text diff. Aligns paragraphs, then word- or
  character-diffs each pair. Runs offline with python-docx; no Word install needed.
when_to_use:
  - Comparing two versions of the same Word document and producing a redline others can review
  - A client or legal returns an edited .docx and you need to see every change as tracked markup
  - Rebuilding "compare documents" without opening Microsoft Word or paying for a diff service
  - Producing a markup file whose changes reviewers can Accept or Reject individually in Word/Google Docs
  - Batch-diffing many version pairs in a pipeline where a GUI is not available
when_not_to_use:
  - Clause-by-clause legal risk assessment of a single contract (use contract-review)
  - Authoring, formatting, or reading a single Word doc with no second version to diff (use docx)
  - Comparing two PDFs rather than .docx files (use pdf to extract text first, then diff)
  - Checking translated-vs-source parity across locales (use i18n-localization-qa)
keywords:
  - redline
  - tracked changes
  - docx
  - word diff
  - compare documents
  - version diff
  - w:ins
  - w:del
  - python-docx
  - markup
  - ooxml
  - contract compare
  - accept reject
  - revision
  - document comparison
similar_to:
  - docx
  - contract-review
  - i18n-localization-qa
  - pdf
inputs_needed: Two .docx files (an OLD/previous version and a NEW/revised version) of the same document; optionally a reviewer name for the change author.
produces: A new .docx containing native tracked-changes markup (insertions and deletions) that Word and Google Docs render under Review > All Markup, ready to Accept/Reject.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# DOCX Redline Compare

Build a **native Word tracked-changes** document from two versions of a `.docx`.
The output is not a text diff or an annotated copy — it contains real OOXML
`<w:ins>` (insertion) and `<w:del>` (deletion) revision elements, so Word,
Word Online, and Google Docs display them under **Review → All Markup** and let a
reviewer **Accept** or **Reject** each change individually.

## When to use

Reach for this when someone asks "what changed between these two Word files?" and
they need a document to mark up and sign off — a returned contract draft, a revised
SOW, a policy update, a new deck script. If they need clause-level legal analysis of
one document, use `contract-review` instead. If there is only one version, use `docx`.

## Prerequisites

- **python-docx** (`pip install --user python-docx`; tested with 1.2.0). Pure Python,
  no Microsoft Word or LibreOffice required.
- Both inputs must be real `.docx` (Office Open XML). Legacy `.doc` won't open —
  convert first. Password-protected files must be decrypted first.
- Only paragraph **body text** is diffed. Tables, headers/footers, footnotes, and
  images are copied structurally-blind (see Pitfalls) — this tool targets prose.

There is **no native python-docx API** for tracked changes; the helper builds the
revision XML directly. That is expected, not a hack — it is how OOXML represents
revisions ([ECMA-376, `w:ins`/`w:del`](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.insertedrun)).

## Recipe: one-shot redline

```bash
python3 scripts/redline_compare.py OLD.docx NEW.docx REDLINE.docx --author "Legal"
```

- `--author "Name"` — the reviewer name stamped on every change (shows in Word's
  markup pane and hover). Defaults to `Redline Compare`.
- `--char` — diff at **character** granularity inside each paragraph. Default is
  **word** granularity, which reads more cleanly for prose. Use `--char` for code,
  reference numbers, or dense legal citations where a one-character change matters.

Open `REDLINE.docx` in Word → **Review → All Markup**. Insertions appear
underlined, deletions struck through, each attributed to `--author`.

## How it works (so you can adapt it)

1. Extract the ordered list of paragraph texts from OLD and NEW.
2. Align paragraphs with `difflib.SequenceMatcher` — `equal` blocks copy through,
   `replace`/`delete`/`insert` blocks are handled pairwise.
3. Within each changed paragraph pair, diff again at word (or char) level and emit
   runs: unchanged text as a plain `<w:r>`, removed text wrapped in
   `<w:del>` (using `<w:delText>`, **not** `<w:t>` — deleted text has its own tag),
   added text wrapped in `<w:ins>`.
4. Every revision gets a unique `w:id`, plus `w:author` and an ISO-8601 `w:date`.

The critical OOXML detail: **deleted text lives in `<w:delText>`, inserted text in
`<w:t>`**. Getting that wrong makes Word silently drop the deletion. The helper
handles it; if you hand-roll, don't forget it.

### Minimal inline snippet

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def wrap_del(text, wid, author, date):
    d = OxmlElement("w:del")
    d.set(qn("w:id"), str(wid)); d.set(qn("w:author"), author); d.set(qn("w:date"), date)
    r = OxmlElement("w:r"); t = OxmlElement("w:delText")  # NOTE: delText, not t
    t.set(qn("xml:space"), "preserve"); t.text = text; r.append(t); d.append(r)
    return d
```

## Verify

Confirm the markup is real and that "Accept All" reproduces NEW exactly:

```bash
python3 - <<'PY'
from docx import Document
from docx.oxml.ns import qn
b = Document("REDLINE.docx").element.body
print("ins:", len(b.findall('.//'+qn('w:ins'))),
      "del:", len(b.findall('.//'+qn('w:del'))),
      "delText:", len(b.findall('.//'+qn('w:delText'))))
# Reconstruct the accept-all text: keep insertions, drop deletions.
for p in b.findall('.//'+qn('w:p')):
    kept = [t.text or "" for r in p.iter(qn('w:r'))
            if r.getparent().tag != qn('w:del')
            for t in r.findall(qn('w:t'))]
    print("ACCEPTED>", "".join(kept))
PY
```

The `ACCEPTED>` lines should match your NEW document. For a human check, open in
Word and toggle **Review → Accept All Changes** — the result must equal NEW.

## Pitfalls

- **Deleted text needs `<w:delText>`.** Put deleted text in a normal `<w:t>` and Word
  drops it. The single most common tracked-changes mistake.
- **Formatting is not diffed.** Bold/italic/style/color changes and run-level
  properties are ignored — only text content. The output re-emits text with default
  formatting, so use this for *content* redlines, not formatting review.
- **Tables, headers/footers, footnotes, images are not covered.** `paragraphs` only
  reads top-level body paragraphs. Content inside tables or other parts is skipped.
  For table-heavy docs, extend the script to walk `document.element.body` cells.
- **Paragraph alignment is text-based.** If a paragraph is both moved *and* edited,
  `SequenceMatcher` may show it as delete+insert rather than an in-place edit. Usually
  fine; for reordered docs the redline can look noisier than a human would write.
- **Whitespace tokens.** Word-mode keeps a trailing space on each token so re-joined
  text spaces correctly; `--char` mode preserves every character exactly.
- **`w:date` must be ISO-8601 UTC** (`YYYY-MM-DDTHH:MM:SSZ`). A malformed date makes
  some viewers hide the timestamp; the helper formats it correctly.
- **Not a substitute for Word's own Compare** for pixel-perfect formatting diffs — but
  it needs no Word license, runs headless, and scales to batches.
