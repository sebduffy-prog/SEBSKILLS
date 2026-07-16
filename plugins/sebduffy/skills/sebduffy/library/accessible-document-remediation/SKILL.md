---
name: accessible-document-remediation
category: documents
description: >-
  Use to make a PDF accessible and legally compliant — tag it for screen
  readers (PDF/UA-1 / ISO 14289), fix WCAG 2.1 AA structure, add alt text and
  reading order, then AUDIT it and prove conformance. Trigger on "make this PDF
  accessible", "PDF/UA", "508 / ADA / EAA compliance", "tag the PDF", "screen
  reader", "alt text", "accessibility remediation", "veraPDF", or the 2026
  ADA Title II / European Accessibility Act deadlines. The plain pdf skill
  reads/merges but NEVER tags — use this when accessibility or compliance is
  the goal.
when_to_use:
  - Making a client, government, or public-body PDF accessible for the 2026 ADA Title II / EAA deadlines
  - Tagging an untagged PDF (headings, lists, tables, alt text, reading order) for screen readers
  - Auditing a PDF against PDF/UA-1 / WCAG 2.1 AA and producing a pass/fail conformance report
  - Converting an existing PDF to PDF/UA with Apryse auto-tagging at scale
  - Triaging a batch of PDFs to find which ones are un-tagged before a compliance push
  - Writing a VPAT / accessibility conformance statement backed by a real validator run
when_not_to_use:
  - Generic read / merge / split / OCR / form-fill on a PDF with no accessibility goal — use pdf
  - Building an accessible slide deck from scratch — use pptx (author tags at source)
  - Making an accessible Word document — use docx (Word's own structure exports clean tags)
  - Auditing a live website / web app for WCAG — that is a browser DOM job, use webapp-testing
  - Localisation / RTL / language-QA of document content — use i18n-localization-qa
keywords: [pdf/ua, accessibility, remediation, wcag, 508, ada, eaa, tagging, screen reader, alt text, reading order, verapdf, apryse, structtreeroot, matterhorn, iso 14289, tagged pdf, compliance audit, vpat, assistive technology]
similar_to: [pdf, docx, pptx, i18n-localization-qa, contract-review]
inputs_needed: The source PDF path(s); the target standard (PDF/UA-1 and/or WCAG 2.1 AA, Section 508, EAA); document language; whether you have an Apryse trial/paid key for auto-tagging or must remediate manually; and Java availability for veraPDF (or use the bundled-JRE installer / Docker).
produces: An accessibility triage report per file, a remediation checklist mapped to Matterhorn/WCAG, a tagged PDF/UA output (when Apryse is available), and a veraPDF conformance verdict you can cite in a VPAT.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Accessible Document Remediation (PDF/UA + WCAG)

Take an inaccessible PDF and make it (a) tagged for assistive technology,
(b) WCAG 2.1 AA structured, and (c) **provably** PDF/UA-1 conformant. Built
for the hard 2026 legal deadlines: **ADA Title II** (US public entities,
compliance from 24 Apr 2026 for large entities) and the **European
Accessibility Act** (EAA, in force 28 Jun 2025). Public-facing PDFs are in
scope.

Do the work in this order — **audit first, remediate, re-validate**. Never
claim compliance without a validator run.

## When to use

An existing PDF must be read by screen readers or must pass a legal
accessibility standard. If the user only wants to extract or merge a PDF with
no accessibility intent, use the `pdf` skill instead.

## Prerequisites (be honest about these)

- **`pypdf`** — installed here (`python3 -c "import pypdf"`), py3.9 fine. Powers
  the local triage script; no license, no network.
- **veraPDF** — the definitive free PDF/UA-1 / PDF/A validator (the reference
  ISO checker). It is **Java** and this Mac has **no Java runtime and no brew**.
  Options: download the veraPDF installer that **bundles its own JRE** from
  <https://verapdf.org/software/> (no system Java needed), or run the Docker
  image `verapdf/verapdfrest`. Do not pretend `verapdf` is on PATH — confirm
  with `command -v verapdf` or `verapdf --version` before quoting a verdict.
- **Apryse SDK** — best automated auto-tagging / remediation, but it is
  **commercial** and installs from a **custom index**, not PyPI:
  `python3 -m pip install apryse-sdk --index-url=https://pypi.apryse.com`.
  Needs a license key (free trial at <https://dev.apryse.com/>) **and** the
  separate **DataExtractionModule** (Doc Structure engine, a large download) —
  auto-tag fails without it. Without a key, remediate manually (Acrobat Pro's
  Accessibility / Reading Order tools, or the source app) and use this skill's
  audit + checklist to drive and verify the work.

## Recipe 1 — Triage a PDF or a whole folder (local, free)

Machine-checkable PDF/UA blockers, straight from the document catalog. A clean
report is necessary-not-sufficient (see Pitfalls), but any FAIL is a hard stop.

```bash
python3 scripts/ua_preflight.py report.pdf
# batch a whole directory:
python3 scripts/ua_preflight.py /path/to/pdfs/*.pdf
```

It checks, per file: **tagged** (`/MarkInfo /Marked true`), **struct-tree**
(`/StructTreeRoot`), document **/Lang**, **title** in metadata **plus**
`ViewerPreferences /DisplayDocTitle true` (so the title, not the filename,
is announced), page **/Tabs /S** tab order, and an XMP metadata stream. Exit
code is non-zero if any file has a hard fail — wire it into CI.

## Recipe 2 — Auto-tag / convert to PDF/UA (Apryse)

Verbatim from Apryse's PDF/UA sample. `AutoConvert` runs the Doc Structure
engine to synthesise the tag tree, reading order and required metadata.

```python
from apryse_sdk import PDFNet, PDFUAConformance, PDFUAOptions, DataExtractionModule

PDFNet.Initialize("YOUR_APRYSE_LICENSE_KEY")
PDFNet.AddResourceSearchPath("/path/to/DataExtractionModule/Lib")  # Doc Structure engine

if not DataExtractionModule.IsModuleAvailable(DataExtractionModule.e_DocStructure):
    raise SystemExit("DataExtractionModule (Doc Structure) not found — auto-tag unavailable")

pdf_ua = PDFUAConformance()
pdf_ua.AutoConvert("in.pdf", "out_pdfua.pdf")            # simple

opts = PDFUAOptions()
opts.SetSaveLinearized(True)                              # fast web view
pdf_ua.AutoConvert("in.pdf", "out_pdfua_linear.pdf", opts)

PDFNet.Terminate()
```

`AutoConvert` is flagged **experimental** by Apryse and is a strong first pass,
not a rubber stamp — it cannot judge whether alt text is *meaningful* or
whether reading order matches visual intent. Always finish with a human review
of Recipe 3's judgment items, then re-validate (Recipe 4).

## Recipe 3 — The human WCAG / Matterhorn checklist

The authoritative failure catalogue is the **Matterhorn Protocol** (31
checkpoints / 136 failure conditions); ~50% are human-only. Work these after
tagging:

- **Headings**: real `H1…H6` tags, no skipped levels, hierarchy matches meaning
  (WCAG 1.3.1). Not just big bold text.
- **Reading order**: the tag tree order equals the logical reading order, not
  the visual placement (1.3.2). Verify with Acrobat's Reading Order / Order panel.
- **Alt text**: every informative image / figure has a concise, meaningful
  `/Alt`; decorative images are marked as **Artifact** so they're skipped (1.1.1).
- **Tables**: `Table > TR > TH/TD`, header cells scoped (`/Scope Row|Column`),
  no layout tables (1.3.1).
- **Lists**: real `L > LI > Lbl + LBody`, not paragraphs with bullet glyphs.
- **Links & controls**: link text makes sense out of context; form fields have
  labels / tooltips and a logical tab order (2.4.4, 3.3.2).
- **Language**: document `/Lang` set, plus per-span `/Lang` on any foreign
  passages (3.1.1 / 3.1.2).
- **Contrast**: text ≥ 4.5:1 (≥ 3:1 for large text) — a visual check, not in the tags (1.4.3).
- **No reliance on colour alone**; no un-tagged content; artifacts (headers,
  footers, page numbers, backgrounds) tagged as **Artifact**.

## Recipe 4 — Validate and prove conformance (veraPDF)

After you have Java (bundled-JRE installer or Docker):

```bash
verapdf --flavour ua1 --format html out_pdfua.pdf > report.html   # PDF/UA-1
verapdf --flavour ua2 out_pdfua.pdf                               # PDF/UA-2
verapdf --flavour 1b  out_pdfua.pdf                               # PDF/A-1b, if also required
```

Flavours: `ua1`, `ua2`, plus PDF/A (`1a 1b 2a 2b 2u 3a 3b 3u 4 …`). Use
`--format xml` for machine parsing, `--format html` for a human report. A clean
`ua1` pass (compliant="true", failedRules=0) is what you cite in the VPAT /
conformance statement. veraPDF checks the *machine-verifiable* PDF/UA rules — it
cannot confirm the Recipe 3 human items, so state both in your report.

## Verify

```bash
python3 -c "import ast,sys; ast.parse(open('scripts/ua_preflight.py').read()); print('syntax ok')"
python3 scripts/ua_preflight.py --help >/dev/null 2>&1 || true   # usage on no-arg
# end-to-end: FAIL on an untagged PDF, PASS after structure is added
python3 scripts/ua_preflight.py yourfile.pdf; echo "exit=$?"
command -v verapdf && verapdf --version   # confirm the validator is actually installed
```

Definition of done: `ua_preflight.py` reports **0 hard fails**, the Recipe 3
checklist is signed off by a human, **and** veraPDF `--flavour ua1` reports
compliant with zero failed rules.

## Pitfalls

- **A clean preflight is NOT conformance.** `ua_preflight.py` and even veraPDF
  only cover machine-checkable rules. Meaningful alt text, correct reading order
  and contrast are human judgments — never sign a VPAT on the script alone.
- **No Java on this Mac.** `verapdf` will not run until you install the
  bundled-JRE build or use Docker. Check `command -v verapdf` first; don't
  fabricate a verdict.
- **Apryse needs the DataExtractionModule**, not just the pip package.
  `AutoConvert` throws without the Doc Structure engine on the resource path.
- **Scanned PDFs are image-only** — OCR them first (see the `pdf` skill,
  pytesseract) so there is real text to tag; tags over a flat image help nobody.
- **Don't remediate at the wrong layer.** If you own the source (Word, InDesign,
  a generator), fix accessibility *there* and re-export — cheaper and more
  durable than patching the PDF. Remediate the PDF only for legacy files you
  can't regenerate.
- **PDF/UA ≠ PDF/A.** They're orthogonal ISO standards; archival mandates may
  require *both* (`ua1` + a PDF/A flavour). Validate each separately.
- **Forms**: an accessible visual form still fails if fields lack `/TU`
  tooltips and a sane tab order — check the AcroForm, not just the page tags.
