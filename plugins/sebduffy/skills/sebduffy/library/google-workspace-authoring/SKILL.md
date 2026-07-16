---
name: google-workspace-authoring
category: documents
description: >-
  Author and edit native Google Slides, Docs, and Sheets programmatically via the
  batchUpdate APIs — build decks, briefs, and trackers with real text, shapes, tables,
  images, charts, and formatting, then share via Drive. Reach for this whenever you must
  PRODUCE or MODIFY a live Google file (not a downloaded .pptx/.docx/.xlsx), template a
  deck by replaceAllText, push rows into a Sheet, or wire an auth flow (OAuth or service
  account) for the Slides/Docs/Sheets v1/v4 REST APIs.
when_to_use:
  - Generating a native Google Slides deck (not a .pptx) from data or an outline
  - Templating a Slides/Docs file by replacing {{placeholders}} via replaceAllText
  - Writing or appending rows/formulas into a live Google Sheet
  - Building a Google Doc brief with headings, bullets, tables, and inline images
  - Setting up OAuth installed-app or service-account auth for the Workspace REST APIs
  - Batching many structural edits into one atomic batchUpdate call
when_not_to_use:
  - Producing a downloadable .pptx file — use the pptx skill instead
  - Producing a downloadable .docx file — use the docx skill instead
  - Producing a downloadable .xlsx file — use the xlsx skill instead
  - Only listing, reading, or copying Drive files with no structural edits — use the Google Drive MCP tools directly
keywords:
  - google slides
  - google docs
  - google sheets
  - batchupdate
  - workspace api
  - replacealltext
  - service account
  - oauth
  - presentations
  - spreadsheets
  - drive
  - deck automation
  - template merge
  - values.update
similar_to:
  - pptx
  - docx
  - xlsx
  - data-driven-deck-generator
  - document-assembly-mail-merge
inputs_needed: >-
  Google Cloud project with Slides/Docs/Sheets APIs enabled, plus credentials
  (OAuth credentials.json OR a service-account JSON via GOOGLE_APPLICATION_CREDENTIALS);
  content/data to author; optional existing fileId to edit.
produces: >-
  A live Google Slides/Docs/Sheets file (by ID and shareable URL) created or edited
  in place, plus reusable Python batchUpdate request payloads.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Google Workspace Authoring (Slides / Docs / Sheets via batchUpdate)

Create and edit *native* Google files programmatically. The Drive MCP can list, read,
and copy files, but it cannot author slide layouts, insert tables, or format text — that
is what the Slides/Docs/Sheets `batchUpdate` REST APIs do, and what this skill covers.

## When to use

Use when the deliverable must be a **live editable Google file** (a URL your team opens
in the browser), not a downloaded Office file. If the user wants a `.pptx`/`.docx`/`.xlsx`
on disk, stop and use `pptx` / `docx` / `xlsx` instead.

## Prerequisites (honest)

- A Google Cloud project with the target APIs enabled: **Google Slides API**, **Google
  Docs API**, **Google Sheets API** (and Drive API for sharing/moving files).
- Credentials — pick one:
  - **OAuth installed app** (interactive, per-user): download `credentials.json` from
    the Cloud Console (OAuth client, type "Desktop app"). First run opens a browser to
    consent; a `token.json` is cached after.
  - **Service account** (headless / CI): set `GOOGLE_APPLICATION_CREDENTIALS` to the SA
    JSON path. Note: a service account has **its own Drive**; files it creates are not in
    your My Drive until you share them to a human or use a Shared Drive / domain-wide
    delegation. For personal decks, prefer OAuth.
- Python 3.9 works. Install once:
  `pip install google-api-python-client google-auth google-auth-oauthlib`
- Helper: `scripts/gws_client.py` handles auth precedence + `create`/`batchUpdate`.

Scopes needed: `presentations`, `documents`, `spreadsheets`, `drive.file`.

## Recipes

All recipes assume `from scripts.gws_client import service, batch_update_slides,
batch_update_docs, batch_update_sheets` (or run `gws_client.py` from its own folder).

### 1. New deck from an outline (Slides)

The reliable pattern: create the presentation, add slides with a predefined `layout`,
then `insertText` into the placeholder shapes. Every object you reference needs an
`objectId` (supply your own — must be unique, 5–50 chars).

```python
svc = service("slides", "v1")
pres = svc.presentations().create(body={"title": "Q3 Media Plan"}).execute()
pid = pres["presentationId"]

requests = [
    {"createSlide": {
        "objectId": "slide_1",
        "slideLayoutReference": {"predefinedLayout": "TITLE_AND_BODY"},
        "placeholderIdMappings": [
            {"layoutPlaceholder": {"type": "TITLE"},  "objectId": "s1_title"},
            {"layoutPlaceholder": {"type": "BODY"},   "objectId": "s1_body"},
        ],
    }},
    {"insertText": {"objectId": "s1_title", "text": "Channel Strategy"}},
    {"insertText": {"objectId": "s1_body",
                    "text": "• Reach\n• Frequency\n• Attention",
                    "insertionIndex": 0}},
]
batch_update_slides(pid, requests)
print("https://docs.google.com/presentation/d/%s/edit" % pid)
```

Draw a free shape instead of a placeholder with `createShape` (EMU units; 914400 EMU = 1
inch): `elementProperties` carries `pageObjectId`, `size` (`width`/`height` as
`{magnitude, unit:"EMU"}`), and `transform` (`scaleX/Y`, `translateX/Y`, `unit`).

### 2. Template-merge a deck or doc (replaceAllText)

Best pattern for branded VCCP templates: build the master once by hand with `{{tokens}}`,
`copy_file` it via the Drive MCP, then swap tokens. Works for Slides **and** Docs.

```python
requests = [
    {"replaceAllText": {
        "containsText": {"text": "{{client}}", "matchCase": True},
        "replaceText": "Cadbury"}},
    {"replaceAllText": {
        "containsText": {"text": "{{date}}", "matchCase": True},
        "replaceText": "July 2026"}},
]
batch_update_slides(copied_presentation_id, requests)   # or batch_update_docs(...)
```

Swap a placeholder image across the deck with `replaceAllShapesWithImage`.

### 3. Structured Google Doc (Docs)

Docs indexes are **UTF-16 offsets into the body**. Insert bottom-up (highest index
first) so earlier inserts don't shift later indices. `location.index` 1 is the start of
the body.

```python
requests = [
    {"insertText": {"location": {"index": 1}, "text": "Creative Brief\n"}},
    {"updateParagraphStyle": {
        "range": {"startIndex": 1, "endIndex": 15},
        "paragraphStyle": {"namedStyleType": "HEADING_1"},
        "fields": "namedStyleType"}},
    {"insertText": {"location": {"index": 15}, "text": "Objective\nDrive salience.\n"}},
    {"createParagraphBullets": {
        "range": {"startIndex": 25, "endIndex": 40},
        "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE"}},
]
batch_update_docs(doc_id, requests)
```

Other useful Docs requests: `insertTable`, `insertInlineImage` (needs a public
`uri`), `updateTextStyle` (bold/color/link), `deleteContentRange`.

### 4. Write values into a Sheet (values API — no batchUpdate needed)

For plain cell values use the **values** endpoints, not `spreadsheets.batchUpdate`.
`valueInputOption`: `RAW` writes strings literally; `USER_ENTERED` parses formulas/dates
(a leading `=` becomes a real formula).

```python
sheets = service("sheets", "v4").spreadsheets()
sheets.values().update(
    spreadsheetId=sid, range="Sheet1!A1:C2",
    valueInputOption="USER_ENTERED",
    body={"values": [["Channel", "Spend", "Total"],
                     ["TV", 50000, "=B2*1.2"]]}).execute()

# Append rows to the first empty row of a table:
sheets.values().append(
    spreadsheetId=sid, range="Sheet1!A1",
    valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
    body={"values": [["Digital", 32000, "=B3*1.2"]]}).execute()
```

Use `spreadsheets.batchUpdate` (the structural one) only for formatting, adding sheets,
conditional formatting, or charts — e.g. `addSheet`, `repeatCell`, `updateCells`,
`addChart`.

## Verify

- Syntax-check the helper before use:
  `python3 -m py_compile scripts/gws_client.py`
- Smoke-test auth + creation (opens a browser once for OAuth):
  `python3 scripts/gws_client.py new-slides "smoke test"` → prints a presentationId.
- Confirm the result: open `https://docs.google.com/presentation/d/<id>/edit` (or
  `/document/`, `/spreadsheets/`), or read it back with the Google Drive MCP
  `get_file_metadata` / `read_file_content`.
- `batchUpdate` returns per-request `replies` — check `createSlide`/`replaceAllText`
  reply counts (e.g. `occurrencesChanged`) to confirm tokens actually matched.

## Pitfalls

- **Downloadable vs live.** This skill makes live Google files. For a file the user
  downloads, use `pptx`/`docx`/`xlsx`. Don't cross the streams.
- **Docs index drift.** Every insert shifts all later indices by the inserted length.
  Either insert last-to-first, or recompute indices after each op. This is the #1 bug.
- **Slides objectId collisions.** IDs must be unique across the presentation and
  5–50 chars matching `[a-zA-Z0-9_-]`. Reusing an ID fails the whole batch.
- **Atomicity.** A `batchUpdate` is all-or-nothing — one bad request rolls back the
  whole call. Build requests incrementally and test small batches first.
- **Service-account invisibility.** SA-created files live in the SA's Drive; you won't
  see them in My Drive. Grant permission (Drive API `permissions.create`) or use OAuth.
- **values vs batchUpdate confusion (Sheets).** Plain cell data → `values().update/append`.
  Formatting/charts/new tabs → `spreadsheets().batchUpdate`. They are different endpoints.
- **replaceAllText is literal by default.** Set `searchByRegex: true` for patterns; watch
  `matchCase`. Tokens that span two text runs (odd formatting) won't match — keep
  placeholders unstyled.
- **API not enabled / scope mismatch.** A `403 SERVICE_DISABLED` means enable the API in
  the Cloud project; a `403 insufficient scopes` means delete `token.json` and re-consent
  after fixing `SCOPES`.
