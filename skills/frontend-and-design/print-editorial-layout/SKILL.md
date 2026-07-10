---
name: print-editorial-layout
category: frontend-and-design
description: >
  Turn HTML/CSS into print-quality paginated PDFs with Paged.js. Use when the user asks for
  running headers/footers, page numbers ("page X of Y"), a table of contents with real page
  references, chapter breaks, crop marks + bleed for the printer, A4/Letter/US-book page sizes,
  left/right (recto/verso) master pages, or a book/report/whitepaper/zine rendered to PDF from
  web tech. Covers the CSS Paged Media @page model, the browser polyfill, and the headless
  pagedjs-cli that shells out to Chromium.
when_to_use:
  - User wants a multi-page PDF (book, report, whitepaper, invoice, zine) generated from HTML/CSS
  - They need running headers/footers, folios (page numbers), or "page X of Y"
  - They need a table of contents whose page numbers are computed automatically
  - They need print production marks — crop marks, bleed, recto/verso master pages
  - They want to preview pagination live in a browser before rendering the final PDF
when_not_to_use:
  - Filling or editing an existing PDF form or merging PDFs — use the `pdf` skill
  - Building a .docx or .pptx deliverable — use the `docx` or `pptx` skill
  - A single-page screen graphic or poster with no pagination — use `canvas-design`
  - Responsive on-screen web layout with no print target — use `fluid-responsive-system`
keywords:
  - pagedjs
  - paged-media
  - print-css
  - pagination
  - running-header
  - page-numbers
  - table-of-contents
  - crop-marks
  - bleed
  - pdf
  - "@page"
  - recto-verso
  - editorial
  - book-layout
  - string-set
  - target-counter
similar_to:
  - fluid-responsive-system
  - professional-page-templates
  - canvas-design
inputs_needed: Content as HTML (or Markdown you convert to HTML), a page size (A4/Letter/custom mm), and whether print marks/bleed are required.
produces: A self-contained HTML file that paginates in-browser via the Paged.js polyfill, plus a print-ready PDF rendered with pagedjs-cli.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Print Editorial Layout with Paged.js

Paged.js is a polyfill for the W3C **CSS Paged Media** and **Generated Content for Paged Media**
specs. You write ordinary HTML plus `@page` CSS; Paged.js fragments the flow into real page boxes
in the browser (for live preview) and `pagedjs-cli` renders the identical result to PDF via a
headless Chromium. Versions verified against **pagedjs 0.4.3 / pagedjs-cli 0.4.3**.

## When to use

Reach for this whenever the deliverable is a *paginated print document* built from web tech and you
need typographic control the browser's own print dialog can't give you: named running headers,
computed folios, a real TOC, and printer marks. If there is no pagination, or the output is Office
formats, use a different skill (see frontmatter).

## Prerequisites

- **Live preview (browser):** just one script tag, no install. Add it at the *end* of `<body>`:
  ```html
  <script src="https://unpkg.com/pagedjs@0.4.3/dist/paged.polyfill.js"></script>
  ```
  The filename is `paged.polyfill.js` (NOT `pagedjs.polyfill.js` — that path 404s). It auto-runs on
  load, replacing your `<body>` flow with `.pagedjs_page` boxes.
- **PDF render (headless):** needs Node ≥ 14 and downloads a Chromium the first time:
  ```bash
  npx pagedjs-cli@0.4.3 book.html -o book.pdf
  ```
  On this macOS box there is no brew; `npx` (bundled with Node) is the path. If Chromium download is
  blocked, point at a system Chrome with `--browserEndpoint <ws-url>`.

## Recipe 1 — Page size, margins, and margin-box headers/footers

`@page` defines the sheet. The 16 **margin boxes** (`@top-center`, `@bottom-right`, …) are where
running content lives. Pull dynamic text from the document with **named strings**.

```css
@page {
  size: A4;                 /* or: Letter | 210mm 297mm | 6in 9in (book) */
  margin: 22mm 18mm;
  /* footer: current folio, centered */
  @bottom-center { content: counter(page); font: 10px/1 Georgia; color: #666; }
  /* header: the current chapter title, set via string-set below */
  @top-left  { content: string(doctitle); font: 9px/1 Georgia; letter-spacing: .08em; }
  @top-right { content: string(chapter);  font: 9px/1 Georgia; color: #999; }
}

h1.doc-title { string-set: doctitle content(text); }   /* captured once */
h2.chapter   { string-set: chapter  content(text); }   /* updates each new chapter */
```

`string(chapter)` resolves to the *last* value set on that page — so the header always tracks the
chapter currently in flow. `content(text)` copies the element's text; you can also use a literal:
`string-set: chapter "Appendix";`.

## Recipe 2 — "Page X of Y" and recto/verso master pages

`counter(pages)` holds the final total (Paged.js resolves it in a second pass). Left/right pages use
the `:left` / `:right` pseudo-selectors so folios sit on the outer edge like a real book.

```css
@page { @bottom-center { content: "Page " counter(page) " of " counter(pages); } }

@page :right { margin-right: 26mm; @bottom-right { content: counter(page); } }
@page :left  { margin-left:  26mm; @bottom-left  { content: counter(page); } }
@page :first { @top-left { content: none; } @top-right { content: none; } } /* bare title page */
@page :blank { @top-center { content: none; } }                            /* padded verso */
```

## Recipe 3 — Chapter breaks and widow/orphan control

Use fragmentation properties, not manual spacing. Named pages let a chapter opener differ.

```css
h2.chapter { break-before: page; page: chapter; }   /* each chapter starts a new page */
@page chapter { @top-left { content: none; } }       /* opener has no running head */

figure, table { break-inside: avoid; }               /* never split a figure across pages */
h2, h3        { break-after: avoid;  }               /* heading never orphaned at page foot */
p             { orphans: 3; widows: 3; }              /* keep ≥3 lines together */
```

`break-before: recto` forces a chapter onto a right-hand page (inserting a blank verso if needed).

## Recipe 4 — Table of contents with real page numbers

`target-counter()` reads the resolved page of whatever the link points at — no manual numbering.

```html
<nav class="toc">
  <a href="#ch1">Introduction</a>
  <a href="#ch2">Methods</a>
</nav>
```
```css
.toc a::after {
  content: leader('.') target-counter(attr(href), page);  /* dotted leader + folio */
}
.toc a { text-decoration: none; color: inherit; }
```
Anchors must match element IDs (`<h2 id="ch1">`). `leader('.')` fills the gap with dots.

## Recipe 5 — Crop marks and bleed for the printer

For professional output the PDF needs trim marks and art that bleeds past the trim. `marks` and
`bleed` are part of the spec and Paged.js honours them.

```css
@page {
  size: 6in 9in;      /* trim size */
  bleed: 3mm;         /* art extends 3mm beyond trim on all sides */
  marks: crop cross;  /* crop (trim) marks + registration crosses */
  marks-crop-color: black;
}
.cover { background: #111; position: absolute; inset: -3mm; } /* fill into the bleed */
```
`pagedjs-cli` writes the bleed + marks into the PDF automatically once these are declared.

## Recipe 6 — Programmatic preview (control the flow yourself)

Skip the auto-polyfill and drive the `Previewer` when you need the page total or post-processing:

```html
<script type="module">
  import { Previewer } from "https://unpkg.com/pagedjs@0.4.3/dist/paged.esm.js";
  const paged = new Previewer();
  const flow = await paged.preview(
    document.querySelector("#content").innerHTML, // source HTML string
    ["print.css"],                                // stylesheets to apply
    document.querySelector("#pages")              // render target
  );
  console.log(`Rendered ${flow.total} pages`);
</script>
```
Do NOT also include `paged.polyfill.js` — that would paginate twice.

## Verify

1. **Preview in a browser** — open the HTML; you should see discrete white page boxes with your
   headers/footers, not one long scroll. Chrome DevTools → each `.pagedjs_page` is a real box.
2. **Render + inspect the PDF:**
   ```bash
   npx pagedjs-cli@0.4.3 book.html -o book.pdf --media print
   # page count sanity check (macOS python3 is 3.9 — pypdf may need: pip3 install pypdf)
   python3 -c "import pypdf,sys; print('pages:', len(pypdf.PdfReader('book.pdf').pages))"
   ```
3. **Check folios and TOC:** open the PDF; confirm `counter(pages)` shows the true total and the TOC
   page numbers match where the anchors actually landed.
4. **Marks:** with `marks: crop cross`, the PDF page is larger than the trim size — the extra margin
   holds the crop marks. If they're missing, the `@page` had no `bleed`/`marks` declared.

## Pitfalls

- **Wrong CDN filename.** It's `paged.polyfill.js`. `pagedjs.polyfill.js` is a common typo and 404s.
- **Script placed in `<head>`.** The polyfill must run after the DOM exists — put it at the end of
  `<body>` (or use `defer`), else it finds nothing to paginate.
- **`counter(pages)` shows 0 or wrong.** It's only correct after Paged.js's second pass. In the live
  preview it settles once rendering finishes; trust the CLI output for the authoritative total.
- **Margin boxes silently empty.** A margin box with no `content` renders nothing. Every folio/header
  needs an explicit `content:` (e.g. `content: counter(page)`), and the `@top-*`/`@bottom-*` box must
  have room — if `margin` is too small the box collapses.
- **`string-set` not updating the header.** The property goes on the *content* element (the `h2`),
  not on `@page`. Retrieve with `string(name)` inside the margin box.
- **`break-before: page` ignored.** Fragmentation applies to block boxes; it won't break inside a
  flex/grid item or a `position: absolute` element. Keep chapter roots as normal block flow.
- **Web fonts don't embed in the PDF.** Self-host or use a webfont `@font-face` with a reachable URL;
  `pagedjs-cli --blockRemote` will strip remote fonts. Prefer local files for reproducible output.
- **Huge documents time out.** Chromium has a default timeout; raise it with `-t 60000` (ms) and
  render in one pass rather than re-running per chapter.
- **Backgrounds/colors missing in PDF.** Rendering already emulates print media; keep colors in CSS
  (Paged.js prints them) — don't rely on the browser's "Background graphics" print checkbox.
