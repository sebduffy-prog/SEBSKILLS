---
name: document-assembly-mail-merge
category: documents
description: >
  Mass-produce personalised Word documents from ONE .docx template plus a data
  source (CSV / JSON / Excel) using docxtpl (python-docx-template). Reach for this
  whenever you need hundreds of near-identical docs — offer letters, contracts,
  certificates, media plans, pitch cover pages, NDAs, invoices, event badges — each
  with per-recipient fields, conditional sections, tables that repeat per row, and
  inline images. Handles Jinja2 logic inside Word, filename templating, and optional
  merge-into-one-file. Use for batch/mail-merge; not single bespoke docs.
when_to_use:
  - Generating many personalised .docx from a template + a spreadsheet/CSV/JSON of recipients
  - Loops that repeat a table row or paragraph per line-item (invoices, schedules, rosters)
  - Conditional sections that appear only when a data field is set (clauses, discounts, add-ons)
  - Inserting per-record inline images (logos, signatures, headshots, QR codes) into each doc
  - Producing one combined .docx (all letters in a single file) as well as per-recipient files
  - Client-safe merge where fields come from a system export, not hand-typed
when_not_to_use:
  - Authoring or editing a single one-off Word document — use the docx skill instead
  - The deliverable is a PDF form/flattened PDF — use the pdf skill
  - The template and output are slides — use the pptx skill
  - Data lives only in a spreadsheet you must reshape first — clean it with the xlsx skill, then return here
keywords:
  - mail-merge
  - docxtpl
  - python-docx-template
  - word-template
  - batch-documents
  - jinja2-docx
  - personalised-letters
  - document-assembly
  - inline-image
  - richtext
  - docxcompose
  - contracts
  - certificates
  - invoices
similar_to:
  - docx
  - pdf
  - xlsx
  - pptx
  - i18n-localization-qa
inputs_needed: A .docx template with Jinja2 tags, a data source (CSV/JSON/xlsx), and an output directory. Optional per-record image files.
produces: One personalised .docx per data row (filename templated), plus an optional single combined .docx.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Document Assembly & Mail Merge (docxtpl)

Turn **one** Word template and **N** rows of data into **N** polished `.docx` files.
The template is a real `.docx` you design in Word/Google Docs — styling, headers,
tables, logos all survive. You drop Jinja2 tags where the variable text goes.

## When to use

Batch personalisation. If you're producing one bespoke document, use `docx`. If you
have a template and a list (10 or 10,000 recipients), this is the skill.

## Prerequisites

- **Python 3.7+** (this Mac ships 3.9 — fine).
- `pip install docxtpl` — pulls in `python-docx`, `jinja2`, `lxml`. Latest is **0.20.2**.
- Optional combine step: `pip install docxcompose` (merges many docs into one file).
- Optional Excel data source: `pip install openpyxl` (or convert to CSV first).
- No LibreOffice/Word needed to generate — docxtpl writes `.docx` directly.

```bash
python3 -m pip install --user docxtpl
```

## How the template works

Author the `.docx` normally, then insert tags. Two families:

**Inline variables & filters** (inside a run — normal text):
- `{{ first_name }}` — replaced, keeps surrounding character styling.
- `{{ amount | round(2) }}` — full Jinja2 filters/expressions.
- `{{r styled }}` — render a `RichText` object (bold/colour/links) built in code.

**Structural tags** — these consume the whole paragraph/row/cell so no stray markup
is left in the doc. This is the part people get wrong:
- `{%p if premium %}…{%p endif %}` — show/hide whole **paragraphs**.
- `{%tr for item in items %}…{%tr endfor %}` — repeat a **table row** per item.
- `{%tc … %}` — operate on a table **cell**; `{% … %}` for logic inside one run.

Rule of thumb: put `{%tr for … %}` in the FIRST cell of the row you want repeated,
and `{%tr endfor %}` in the first cell of a trailing row. Same idea for `{%p %}`.

## Recipe 1 — Batch merge with the helper script (the common case)

`scripts/mail_merge.py` takes a template + CSV/JSON and writes one doc per row.

```bash
# CSV header row = your template field names.
python3 scripts/mail_merge.py offer_template.docx recipients.csv out/ \
    --name "{{last_name}}-{{first_name}}-offer.docx"

# Merge everything into a single reviewable file as well:
python3 scripts/mail_merge.py offer_template.docx recipients.csv out/ \
    --name "{{last_name}}.docx" --combine all_offers.docx

# Validate template + data and preview filenames WITHOUT writing docs:
python3 scripts/mail_merge.py offer_template.docx recipients.csv out/ --dry-run
```

`--name` reuses `{{field}}` tokens from your data; unsafe filename characters are
sanitised, and `{{index}}` (0-based row number) is always available.

## Recipe 2 — Full control in Python (images, RichText, tables, conditionals)

When you need inline images or dynamic styling, render directly:

```python
from docxtpl import DocxTemplate, InlineImage, RichText
from docx.shared import Mm

doc = DocxTemplate("template.docx")

context = {
    "client": "Warner Music",
    "campaign_live": True,                      # drives {%p if campaign_live %}
    "line_items": [                             # drives {%tr for row in line_items %}
        {"channel": "TikTok", "spend": 42000},
        {"channel": "Meta",   "spend": 31500},
    ],
    "total": 73500,
    "logo": InlineImage(doc, "vccp_logo.png", width=Mm(35)),
    "note": RichText("URGENT", color="FF0000", bold=True),   # used as {{r note }}
}
doc.render(context)
doc.save("warner_media_plan.docx")
```

- Build a **fresh `DocxTemplate` per document** in a loop — instances are stateful and
  cannot be re-rendered. (The helper already does this.)
- `InlineImage(doc, path, width=Mm(...))` — units are `Mm`, `Inches`, or `Pt` from
  `docx.shared`; used in the template as plain `{{ logo }}`.
- `RichText(text, color="FF0000", bold=True, size=..., font=...)`; add hyperlinks with
  `rt.add("click", url_id=doc.build_url_id("https://..."))`; template tag is `{{r var }}`.

## Recipe 3 — Excel as the data source

```python
import openpyxl
wb = openpyxl.load_workbook("recipients.xlsx")
ws = wb.active
headers = [c.value for c in ws[1]]
rows = [dict(zip(headers, [c.value for c in r])) for r in ws.iter_rows(min_row=2)]
# then loop rows exactly like Recipe 2, or dump rows to JSON and use the helper.
```

## Recipe 4 — Embed an existing .docx per record (subdocuments)

```python
sd = doc.new_subdoc("standard_terms.docx")   # merge a whole existing doc in
doc.render({"terms": sd})                     # template tag: {{p terms }}
```

## Verify

- **Undeclared vars sanity check** before a big run:
  ```python
  from docxtpl import DocxTemplate
  print(DocxTemplate("template.docx").get_undeclared_template_variables())
  ```
  Every name printed must be a key in your context (or a Jinja global), or render fails.
- `--dry-run` lists planned filenames and parses the template without writing files.
- Open 2-3 generated docs in Word: confirm no literal `{{ }}` / `{% %}` remain, tables
  repeated the right number of rows, and conditional sections appeared/vanished correctly.
- Count outputs: files in `out/` should equal data rows.

## Pitfalls

- **Word splits your tag across runs.** If `{{ name }}` renders literally, Word stored
  it as `{{ na` + `me }}`. Fix: delete and retype the tag in one go, or paste it as plain
  text (clear formatting) so it lives in a single run.
- **Curly-quote / autocorrect corruption.** Turn off Word autocorrect while typing tags;
  `“ ”` are not `" "` and Jinja won't parse them.
- **Structural vs inline confusion.** Using `{% for %}` (inline) where you meant
  `{%tr for %}` leaves broken table markup. Repeats over rows/paragraphs need the
  `p`/`tr`/`tc` prefixed forms.
- **Reusing one DocxTemplate in a loop** silently produces wrong/empty output — new
  instance per doc.
- **`docxcompose` not installed** → `--combine` raises ImportError. Per-file output still
  works; install it only if you need the single merged file.
- **Numbers from Excel** may arrive as floats (`42000.0`); format in the template
  (`{{ "{:,.0f}".format(spend) }}`) or coerce in Python.
- **Client data hygiene:** treat the data source as untrusted input — spot-check a sample
  before shipping hundreds of docs to named recipients.
