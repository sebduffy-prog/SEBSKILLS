---
name: vccp-media-design
category: frontend-and-design
description: >
  Apply the VCCP Media 2026 brand system to any client-facing artifact —
  web pages, web apps, dashboards, slide decks (PPTX / Keynote / Google
  Slides), PDF reports, posters, infographics, social tiles, banners,
  print collateral, editorial covers, matplotlib charts. Mustard
  (#FFC931) primary half + Teal (#80E8E3) appendix half on white paper,
  Inter Tight typography throughout, sentence-case copy, the signature
  highlighter parallelogram (skewX -12deg) behind italic accent words,
  tabular numbers, no border-radius, no gradients, no red/green deltas.
  Trigger on any of: "VCCP", "VCCP Media", "VCCP brand", "VCCP slides",
  "VCCP deck", "VCCP poster", "VCCP report", "VCCP infographic",
  "in the VCCP look", "make this VCCP", "VCCP highlighter", "mustard
  and teal brand", "VCCP Media Modeller styling", or any user mention
  of mustard + teal + Inter Tight + highlighter motif together. SKIP
  when the user explicitly requests a different agency, a different
  brand, or Anthropic styling (use `brand-guidelines` instead).
when_to_use:
  - Styling a web page, web app, or dashboard in the VCCP Media 2026 look (two-pane shell, rail/frame cards, mustard nav pill)
  - Building a VCCP or VCCP Media slide deck — always cloned from the matching file in the real template gallery (`~/Desktop/VCCP Templates/`), never from scratch
  - Producing a VCCP-branded PDF report, poster, infographic, or editorial/report cover (ReportLab / WeasyPrint / InDesign recipes)
  - Making matplotlib charts in the VCCP palette with Inter Tight and the vccp_charts rcParams config
  - Creating social tiles, banners, email signatures, or business-card collateral with the highlighter parallelogram motif
  - Placing the official VCCP Media logo lockups (Logo, Bear, Girl, Girl_and_Bear PNGs) with correct sizing and clear space
when_not_to_use:
  - The user asks for a different agency's or client's brand, or Anthropic styling — use brand-guidelines instead
  - Recolouring the VCCP logo for client-branded surfaces — that is the separate vccp-logo-use skill
  - Generic non-branded UI work with no VCCP requirement — use frontend-design or theme-factory
keywords: [vccp, vccp media, mustard, teal, eggshell, inter tight, highlighter, parallelogram, brand system, slide deck, pptx, pdf report, poster, infographic, social tile, matplotlib, dashboard, editorial, logo lockup, sentence case, tabular numbers, wlv]
similar_to: [brand-guidelines, theme-factory, frontend-design, WLV]
inputs_needed:
  - Which artifact type (web/dashboard, PPTX deck, PDF report, poster, infographic, social tile, chart, collateral)
  - Which half is primary — mustard (operator-facing/hero, the default) or teal (research/methodology/appendix)
  - Headline copy as a sentence, plus which single word gets the highlighter accent
  - Output dimensions/format where relevant (A4/A3, poster size, tile size, 16:9 deck)
produces: A VCCP Media 2026-branded artifact (web UI, PPTX deck on the official template, PDF, poster, infographic, chart, or social tile)
status: stable
owner: seb.duffy
updated: 2026-07-24
---

# VCCP Media 2026 — design system

A single skill covering every artifact VCCP Media outputs: from a
working web tool to a printed poster. The brand is editorial-modern,
not SaaS — flat colour, sentence-case copy, generous whitespace, the
parallelogram highlight as the recurring motif.

The reference implementation lives next to this file as
[`example.html`](example.html). Open it in a browser to see every
component in context. The MMM tool repo holds the production
implementation: `frontend/brand/vccp.css` (web),
`mmm_tool/export/vccp_brand.py` (PPTX primitives),
`mmm_tool/export/vccp_charts.py` (matplotlib).

**Full editable template gallery (source of truth for decks):**
`~/Desktop/VCCP Templates/` — see "Slide decks" below.

---

## Two brands, not one — VCCP vs VCCP Media

These are **separate brand instances that share one palette and one
type family**. Don't conflate them:

| | **VCCP** (corporate/master brand) | **VCCP Media** (this skill's default) |
|---|---|---|
| Source of truth | `VCCP Templates/VCCP/_VCCP Brand Guidelines_Dec 2025.pptx` | `VCCP Templates/VCCP MEDIA/*.pptx` (8 templates) |
| Second colour's official name | **Eggshell** `#80E8E3` — "premium, refined moments" | Same hex, referred to as **teal** in this skill's own production code (`mmm_tool`) |
| Framing of the two-colour split | Mustard = "spicy, punchy, stand-out impact" vs Eggshell = "premium, refined" — pick one per page, context-led | Mustard = primary/hero/operator-facing vs teal = appendix/research/methodology |
| Distinctive corporate elements | **The Frame** (4 logo-lockup frame types) and **Patterns** (VCCP Text / Girl & Bear / Stairway 1 / Stairway 2) — see below. VCCP Media decks do not use these. | Rail cards, frame cards (web/PPTX card vocabulary below), stage-number chips |
| When to reach for it | Group-wide comms, brand guideline requests, anything explicitly "VCCP" (not "VCCP Media") | Anything client-facing from the media agency: pitches, credentials, strategy decks, reports |

Same **non-negotiables across both**: Inter Tight only, sentence case
only, Mustard and Eggshell/Teal never mixed on the same page, black
is the only accessible text colour on any brand colour or tint, and
the highlighter parallelogram rules below apply identically in both.

If a request just says "VCCP" with no "Media", ask (or infer from
context — an external client artifact almost always means VCCP
Media) rather than silently picking one.

---

## TL;DR — the six rules

1. **Pick one half.** Mustard is the primary surface for operator-
   facing / hero / cover artifacts. Teal/Eggshell is the appendix
   half: research, methodology, supporting material, or the
   "premium/refined" register on the corporate brand. Never split a
   single composition 50/50 between them, and never use both as
   full-bleed colour on the same page.
2. **Sentence case, Inter Tight, all weights 300–700.** No serifs,
   no monospace pairings, no Title Case or UPPERCASE headlines
   (caps allowed only sparingly in chart/caption labels).
3. **The highlighter parallelogram** — a solid brand-colour box,
   **no outline**, sent to the **back** so text sits on top, behind
   **one word or a short phrase only** (never a full line or
   multiple lines) — is the single recurring motif. See the
   dedicated section below; this has been a recurring source of
   off-brand output, read it before touching one.
4. **Square corners, no gradients, no rounded buttons.** Editorial,
   not SaaS. The only rounded element is the nav pill.
5. **Tabular numbers, ink-on-paper or paper-on-ink for contrast.**
   No red/green deltas — up is `--teal-deep`, down is `--mustard-dark`.
6. **Titles get personality, bodies don't.** Headline/title copy is
   written in the WLV (Write Like Vallance) register — witty,
   erudite, one memorable turn of phrase, still one sentence-case
   line. Every other line — body copy, bullets, captions, chart
   labels — is British English, zero em/en dashes, plain and
   analytical, no rhetorical flourish. See "Writing rules" below.

---

## Palette

```css
:root {
  /* MUSTARD — primary half */
  --mustard:        #FFC931;   /* signature surface, CTAs, active state */
  --mustard-dark:   #FF8812;   /* warnings, down-deltas */
  --mustard-light:  #FFEDBB;   /* highlighter fill */
  --mustard-pale:   #FFF9E2;   /* card surfaces, frame panels */

  /* TEAL — appendix half */
  --teal:           #80E8E3;   /* research cover fill, brain accents */
  --teal-deep:      #00BCA5;   /* method nodes, up-deltas, validated states */
  --teal-light:     #BDF9F6;   /* teal-variant highlighter fill */
  --teal-pale:      #DEFCFA;   /* research card surfaces */

  /* Neutrals */
  --ink:            #000000;
  --ink-soft:       #1A1A1A;   /* body copy on warm paper */
  --paper:          #FFFFFF;
  --paper-warm:     #FBF8F0;   /* secondary surfaces, chat streams */
}
```

PPTX (`python-pptx`) equivalents:

```python
from pptx.dml.color import RGBColor
MUSTARD      = RGBColor(0xFF, 0xC9, 0x31)
MUSTARD_DARK = RGBColor(0xFF, 0x88, 0x12)
MUSTARD_LITE = RGBColor(0xFF, 0xED, 0xBB)
MUSTARD_PALE = RGBColor(0xFF, 0xF9, 0xE2)
TEAL         = RGBColor(0x80, 0xE8, 0xE3)
TEAL_DEEP    = RGBColor(0x00, 0xBC, 0xA5)
TEAL_LITE    = RGBColor(0xBD, 0xF9, 0xF6)
TEAL_PALE    = RGBColor(0xDE, 0xFC, 0xFA)
INK          = RGBColor(0x00, 0x00, 0x00)
PAPER        = RGBColor(0xFF, 0xFF, 0xFF)
PAPER_WARM   = RGBColor(0xFB, 0xF8, 0xF0)
```

**Naming note:** the official VCCP corporate brand guidelines call
`#80E8E3` **Eggshell**, not teal. "Teal" is this skill's own
(VCCP Media / `mmm_tool`) internal name for the same hex. Use
"Eggshell" when writing about or presenting the corporate brand;
"teal" is fine for VCCP Media internal/dev-facing artifacts. They
are the same colour — never introduce a second, slightly-different
teal.

Print / CMYK approximations (proof on your press):
- Mustard `#FFC931` → C0 M21 Y82 K0
- Teal    `#80E8E3` → C46 M0 Y15 K0
- Ink     `#000000` → C0 M0 Y0 K100 (or rich-black C40 M30 Y20 K100 for large fills)

**Dominance rule.** Mustard occupies 60–70% of any composition's
visual weight. Teal earns its place only on research / appendix
surfaces or as a single accent. Black ink and white paper are
load-bearing — they're not "negative space," they hold both halves
together.

---

## Typography

**Inter Tight** for every weight 300–700, italic 400 and 500. No
serif companion, no monospace pairing. Italic is reserved for the
highlighter accent word.

```css
--font-sans: 'Inter Tight', system-ui, -apple-system, 'Segoe UI', sans-serif;

--t-xl: clamp(2.4rem, 4.4vw, 4.2rem);   /* cover headlines */
--t-lg: clamp(1.8rem, 2.6vw, 2.6rem);   /* card titles, slide titles */
--t-md: clamp(1.15rem, 1.4vw, 1.4rem);  /* sub-heads, lede */
--t-sm: 0.93rem;                         /* body, table cells, captions */
--t-xs: 0.78rem;                         /* eyebrows, metadata, page nos */
```

**Weights**

| Element | Weight |
|---|---|
| Headlines | 500 (medium) — never 700 |
| Body | 400 |
| Eyebrows, table heads, captions | 600 + UPPERCASE + `letter-spacing: 0.08em` |
| The highlighted word | 500 italic |

**Sentence case everywhere.** Read every headline like editorial
copy: *"Smarter spend decisions, backed by real causal evidence."*
Not "SMARTER SPEND DECISIONS." Title Case is also wrong.

**Numbers.** `font-variant-numeric: tabular-nums` on every metric,
every table cell. Always. Misaligned digits in a numerical column
are the single biggest "this looks AI-generated" tell.

For PPTX / matplotlib: bundle the Inter Tight TTFs and register
them via fontconfig *before* any chart render. Production pattern
lives in `mmm_tool/export/vccp_charts.py`. For PDFs from
ReportLab / WeasyPrint, embed the OTF/TTF in the document
metadata — don't rely on system fallback.

---

## The signature motif: highlighter parallelogram

The single most distinctive element, and the one that has gone wrong
most often — read this whole section before placing one.

**This is a documented corporate rule**, not a house convention this
skill invented (see `_VCCP Brand Guidelines_Dec 2025.pptx`, slides
16–17, "Typography / Highlighter"), verified in Dec 2025 against
**358 real instances** across the whole VCCP Media template gallery
(`~/Desktop/VCCP Templates`). The rule, verbatim from the guidelines:

> Select the parallelogram shape. Draw it over the word/phrase you
> want to highlight. Change the colour to a brand colour and ensure
> there is no outline. Move the shape to the back so the text sits
> on top. You can adjust the angle if you want to add more variety.
> The highlighter is already set up in our PPT template.

### The rules, made explicit

1. **One word or one short key phrase only — never a full line, and
   never spans multiple lines.** This is an explicit "Don't" in the
   guidelines (slide 17, #6). If the copy needs more than a phrase
   highlighted, don't highlight it — shorten the copy instead.
2. **Solid brand-colour fill, zero outline.** Verified in the real
   files: every one of the 358 instances has `line.fill.type =
   BACKGROUND` and `line.width = 0`. Never add a stroke, however
   thin.
3. **Sent to the back, text on top.** Verified: in every real
   instance the shape sits at or near index 0 of its slide's shape
   z-order (added first, i.e. furthest back). Get the z-order wrong
   and the highlight covers the word instead of sitting behind it.
4. **The word on top is Light Italic** (headline highlight) or
   **SemiBold** (body highlight) — never Medium. Matches the
   guidelines' font-weight table exactly (see Typography above).
5. **Angle can vary "for variety" — but only by reusing the
   template's own shape, never by hand-drawing a fresh one and
   eyeballing the skew.** This is the actual failure mode behind
   "parallelograms have been an issue": duplicate an existing
   highlighter instance from the template (`Ctrl/Cmd+D`, or
   `copy.deepcopy` in python-pptx) and reposition/restretch the
   copy; don't insert a brand-new `MSO_SHAPE.PARALLELOGRAM` from the
   shapes menu and set your own adjustment value.
6. **If you must build one from scratch, use `adjustments[0] =
   0.25`, not any other value.** This was previously documented in
   this skill as `0.08` (≈ a shallow, near-upright shear) — that is
   **wrong**. Auditing every parallelogram in the real template
   gallery: 340 of 358 (95%) use `adj = 0.25`, which is also
   PowerPoint's own stock default the moment you drop a parallelogram
   onto a slide from the shapes menu. Don't invent a custom skew —
   the brand default already *is* the tool's default.
7. **Never independently stretch width vs height on a duplicated
   highlighter without checking the result.** The visual skew is a
   function of the shape's `adj` value combined with its own
   width:height ratio, so squashing a copy to cram in a long word (or
   over-widening one for a short word) visibly changes how skewed it
   looks next to its neighbours on the same slide, even with `adj`
   unchanged. If a duplicate looks off after resizing, prefer
   widening evenly or nudging font size instead of only changing one
   dimension.

```html
<h1>Smarter <em class="hl">spend</em> decisions, backed by real
    <em class="hl">causal</em> evidence.</h1>
```

```css
.hl {
  font-style: italic;
  font-weight: 500;
  position: relative;
  display: inline-block;
  /* Tight line-height + zero horizontal padding so the box is
   * exactly glyph-width. Skew then adds ~0.10em halo on each side
   * which reads as centred. */
  line-height: 0.85;
  padding: 0.08em 0;
  z-index: 0;
}
.hl::before {
  content: "";
  position: absolute;
  inset: 0 -0.06em;
  background: var(--mustard-light);
  transform: skewX(-12deg);
  transform-origin: 50% 50%;
  z-index: -1;
  pointer-events: none;
}
.hl-teal::before { background: var(--teal-light); }
```

**Failure modes to avoid:**

- Positive horizontal padding → parallelogram visibly wider than
  the word, skew pushes it right of the glyph
- Forgetting `font-style: italic` → slant of the box doesn't match
  the letterforms and the whole thing looks broken
- Highlighting both the verb *and* the noun in the same phrase →
  visual noise; one per phrase, max two per slide cover
- Highlighting a whole line or spanning a line break → explicit
  brand "Don't"; shorten the copy instead
- Mustard highlighter on a mustard surface → invisible. Use
  `.hl-teal` variant or invert to ink-on-paper for the whole text
- A freehand/resized parallelogram whose skew visibly doesn't match
  the others on the same slide or deck

**For PPTX**: the highlighter is a `MSO_SHAPE.PARALLELOGRAM` filled
with a brand colour (`MUSTARD_LITE` or `TEAL_LITE`), no border,
behind a transparent text frame, sent to the back of the shape
z-order. Prefer **duplicating** an existing highlighter shape from
the template over building a new one; if building fresh,
`adjustments[0] = 0.25` (see rules above — this replaces the old,
incorrect `0.08` value). See
`mmm_tool/export/vccp_brand.py::add_highlight_text()` and the
cloning method in
[`references/pptx-template-population.md`](references/pptx-template-population.md).

**For print / poster**: draw it as a hand-tilted Pantone-equivalent
flat fill in InDesign; never reproduce as a gradient or with a
drop shadow.

**Use sparingly.** Reserved. If you put one on every slide it
stops being signature.

---

## Card vocabulary (web, slides, PDF)

Three variants. Every surface in the system is one of these.

```css
/* Base — neutral white card with soft shadow */
.vccp-card {
  background: var(--paper);
  padding: 28px 28px 32px 32px;
  border: 1px solid rgba(0,0,0,0.06);
  box-shadow:
    0 1px 0 rgba(0,0,0,0.04),
    0 8px 24px rgba(0,0,0,0.04);
  transition: box-shadow .25s ease;
}
.vccp-card:hover {
  box-shadow:
    0 2px 0 rgba(0,0,0,0.06),
    0 18px 40px rgba(0,0,0,0.08);
}

/* Rail — 3px mustard left bar. The DEFAULT for input/form cards. */
.vccp-rail { border-left: 3px solid var(--mustard); }

/* Frame — full ink hairline border + mustard-pale fill.
   Hero / divider / "editorial moment" surfaces only. */
.vccp-frame {
  border: 1.5px solid var(--ink);
  background: var(--mustard-pale);
  box-shadow: none;
}
```

**Rail is the default.** Frame is for editorial moments —
exec-summary cover, divider slides, the export panel, a quote
pull-out. Don't frame ten cards on the same page; the motif loses
its weight.

For PPTX: `rail_border()` draws a 3pt mustard rectangle pinned to
the slide's left edge. `frame_border()` draws a 1.5pt ink rectangle
inset by 0.4". Both helpers in `mmm_tool/export/vccp_brand.py`.

---

## Stage-number chip

The numbered marker that prefixes each stage card / chapter / step.
Always inside a black-bordered mustard chip with letter-spaced caps.

```html
<header class="vccp-card-head">
  <span class="vccp-stage-num">01</span>
  <h2 class="vccp-card-title">Tell <em class="hl">us</em> about the run</h2>
  <p class="vccp-card-sub">Drop your data and set the brief.</p>
</header>
```

```css
.vccp-stage-num {
  display: inline-block;
  font-weight: 500;
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  background: var(--mustard);
  border: 1px solid var(--ink);
  padding: 4px 8px;
  margin-bottom: 14px;
}
```

Use 01 / 02 / 03 — never "Step 1" or roman numerals. Two digits
always (so "07", not "7"). Reads as editorial pagination.

---

## Brand lockups — the four official logos

The bear and the girl. Both as silhouettes, in four lockups. The four
PNGs live in [`assets/logos/`](assets/logos/) next to this file —
**always reference them from there**, never re-trace, redraw, or use
emoji substitutes.

| File | Dimensions | Aspect | Where to use |
|---|---|---|---|
| [`Logo.png`](assets/logos/Logo.png) | 1620 × 1620 | 1:1 | **Primary mark.** Bear + girl + "VCCP / Media" wordmark stacked. App icons, profile avatars, slide-deck covers + back covers, business cards, the favicon source. |
| [`Bear_Lockup.png`](assets/logos/Bear_Lockup.png) | 1920 × 1080 | 16:9 | Bear-only silhouette on transparent. Hero banners, sub-brand cards, large-format posters where the wordmark would be redundant. |
| [`Girl_Lockup.png`](assets/logos/Girl_Lockup.png) | 1080 × 1080 | 1:1 | Girl-only silhouette on transparent. Editorial spacers, end-credits, social tiles where the bear is too heavy. Pairs with `Bear_Lockup` across opposing pages. |
| [`Girl_and_Bear.png`](assets/logos/Girl_and_Bear.png) | 2880 × 1620 | 16:9 | Both silhouettes facing each other on transparent. The scale-comparison artwork — open-event banners, conference splash, hero artwork where the whole story matters. **Not** the primary mark; use `Logo.png` for branding. |

### Sizing rules (use these, don't improvise)

| Surface | Logo / mark height | Notes |
|---|---|---|
| Web nav left | **32 – 40px** | Use `Logo.png` cropped to square favicon-style, or just the bear inset from `Bear_Lockup.png` |
| Web hero | **96 – 160px** | Centred on cover slides only; never on body sections |
| Slide cover (1920 × 1080) | **220 – 280px tall** | `place_logo_centered(slide, height=Inches(2.6))` |
| Slide footer | **never** | Body slides use page number + `© VCCP Media YYYY` only |
| Poster (A1 / A0) | **15-22% of short edge** | Bottom-right or bottom-centre |
| Social tile (1080²) | **96 – 128px** | One corner, never centred unless it's the *only* element |
| Favicon | **32 / 64 / 180** | Crop `Logo.png` to the bear+girl horizontal baseline portion (top ~55%); discard wordmark |
| Email signature | **80px tall max** | `Logo.png` only |

### Clear-space + safety

- **Clear space = 1× the cap-height of "V" in the wordmark** all
  sides. Roughly 15% of the lockup's longest edge. Never crowd.
- **Minimum size:** 24px height on screen, 8mm in print. Below that,
  the bear's fur breaks up.
- **Never stretch or skew.** Always proportional. Use `object-fit:
  contain` in HTML, `Inches(h * ratio)` in python-pptx, no negative
  scale in InDesign.

### What never to do

1. **Don't redraw or vectorise from scratch.** Use the supplied PNGs.
2. **Don't recolour for VCCP-branded surfaces.** Black silhouette is
   the rule. (For *client-branded* surfaces, use the separate
   [[vccp-logo-use]] skill — same files, controlled recolour.)
3. **Don't combine with other logos at the same hierarchy level.** If
   it's a co-branded surface, put a vertical hairline divider and let
   each mark breathe.
4. **Don't animate the silhouette.** A gentle fade or scroll-in is
   fine; rotation, distortion, or "shake" is not.
5. **Don't crop the bear off the baseline in `Logo.png`** — the
   baseline is part of the lockup.
6. **Don't place on mustard.** The black silhouette competes with the
   mustard surface and visually crowds the highlighter motif. Logos
   go on paper or ink only.

### Web implementation

```html
<img
  src="/brand/Logo.png"
  alt="VCCP Media"
  width="160"
  height="160"
  style="display: block; object-fit: contain;"
/>
```

For dark surfaces, drop in `Logo.png` and add a subtle paper-coloured
"plate" behind it rather than recolouring the PNG. Recolouring on
VCCP surfaces is not a permitted variant.

### PPTX implementation

```python
# mmm_tool/export/vccp_brand.py
from pptx.util import Inches
from PIL import Image

LOGO_PATH = Path(__file__).parent / 'assets' / 'logos' / 'Logo.png'

def place_logo_centered(slide, height=Inches(2.6)):
    img = Image.open(LOGO_PATH)
    ratio = img.width / img.height
    width = height * ratio
    left = (SLIDE_W - width) / 2
    top = Inches(0.6)
    slide.shapes.add_picture(str(LOGO_PATH), left, top, width=width, height=height)
```

Pin to cover + back-cover only; body slides keep the footer + page
number identity instead.

---

## Per-medium recipes

### Web UI / dashboard / web app

Canonical layout is a two-pane shell — 40vw input rail on the left,
60vw output canvas on the right. Used by every operator-facing tool
in the system.

```css
.vccp-shell {
  display: grid;
  grid-template-columns: 40vw 60vw;
  min-height: calc(100vh - 57px);
}
.vccp-left  { border-right: 1px solid var(--ink); padding: clamp(20px, 2.5vw, 40px); background: var(--paper-warm); }
.vccp-right { padding: clamp(20px, 2.5vw, 40px); background: var(--paper); }

@media (max-width: 1024px) {
  .vccp-shell { grid-template-columns: 1fr; }
  .vccp-left  { border-right: 0; border-bottom: 1px solid var(--ink); }
}
```

Nav: 57px tall, ink hairline bottom, brand mark left, tab pills
right. Active tab gets `background: var(--mustard); border: 1px
solid var(--ink); border-radius: 999px;` — the pill is the *only*
rounded element in the whole system.

Buttons (square, no radius):

```css
.vccp-btn         { background: var(--mustard); border: 1px solid var(--ink); padding: 12px 18px; font-weight: 500; }
.vccp-btn-primary { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.vccp-btn-quiet   { background: transparent; border-color: rgba(0,0,0,0.2); color: rgba(0,0,0,0.6); }
.vccp-btn:hover   { transform: translateY(-1px); box-shadow: 0 2px 0 var(--ink); }
```

Floating-label inputs only — the placeholder is a single space, the
real label floats up on `:placeholder-shown` transition.

### Slide decks (PPTX / Keynote / Google Slides)

**The full editable template gallery lives at
`~/Desktop/VCCP Templates/`** (all `.pptx` — never `.odp`/PDF exports
of these, see "Do not" below). Eight VCCP Media templates plus the
one VCCP corporate guidelines deck. **Always build ON the matching
file below**, never from `Presentation()` scratch: cloning real
slides preserves the master, layouts, theme and brand furniture, so
anyone who opens the result afterwards in PowerPoint or Google Slides
gets the real template look, not an imitation.

| File | Use it for | Slides | Canvas |
|---|---|---|---|
| `Pitch Template 2026 [Q2].pptx` | General new-business pitch decks — the widest archetype gallery, use this as the default when nothing more specific fits | 133 | 16:9, 10800000×6076800 EMU |
| `Strategy & Planning Template 2026 [Q2].pptx` | Strategy / planning decks | 129 | 16:9, same EMU |
| `VCCP Media Creds 2026 [Q1].pptx` | Capabilities / credentials decks | 63 | 16:9, same EMU |
| `Portrait Template A4 2026 [Q2].pptx` | A4 portrait one-pagers / documents | 28 | A4 portrait |
| `VCCPx Ideas Book TEMPLATE 118x210 2026 [Q2].pptx` | Small printed "ideas book" pages — strict bleed/safe-area rules baked into slide 1, read it before adding pages | 3 | 118×210mm |
| `TRUMP CARD MASTER A5 2026 [Q2].pptx` | Staff/team "trump card" bio cards | 13 | A5 |
| `SOAP & POAP A4 2026 [Q2].pptx` | Single-page strategy/creative-platform frameworks (objective, audience, growth levers, OESP) | 2 | A4 portrait |
| `VCCP Media CIM Card 2026 [Q2].pptx` | Single category-insight-map card (role of advertising / media behaviours / segment) | 1 | 16:9 |

Canvas for the 16:9 decks is **10800000 × 6076800 EMU**
(= 11.8110" × 6.6457"; `Inches(11.811) × Inches(6.646)` is within
rounding — compare with a tolerance, never exact-equality).

The template theme IS the brand palette (verified in `theme1.xml`):
`dk1` ink `000000` · `lt1` paper `FFFFFF` · `dk2` mustard `FFC931` ·
`lt2` teal/eggshell `80E8E3` · `accent1` mustard-dark `FF8812` ·
`accent2` mustard-light `FFEDBB` · `accent3` teal-deep `00BCA5` ·
`accent4` teal-light `BDF9F6` · `accent5` mustard-pale `FFF9E2` ·
`accent6` teal-pale `DEFCFA`. The theme's latin face reads "Arial"
(Google Slides export artifact — all these files were built in
Slides then exported, hence shape names like `Google Shape;1026;p101`)
— set **Inter Tight** explicitly on every run; the real text runs
already carry `Inter Tight Light` / `Medium` / `SemiBold`, only the
theme default is wrong.

**Layout names are not archetype labels.** Each slide in these files
has its own auto-generated Google-Slides-export layout name (e.g.
`TITLE_AND_BODY_1_4_2_5_1_3`) — there is roughly one unique layout
per slide, not a small reusable set, so `slide_layout.name` is
useless for finding "the quote slide" or "the divider slide".
**Find archetypes by placeholder marker text instead** — see the
full worked method and the marker table (cover, quote, headline+body,
agenda, divider, closing, etc., with real slide indices per file) in
[`references/pptx-template-population.md`](references/pptx-template-population.md).

**Every slide carries:**

- Footer bottom-right: `© VCCP Media YYYY` + `page NN` in 8.5pt
  letter-spaced caps, ink, full opacity (not faded)
- Source caption bottom-left in 8.5pt grey when external data is
  cited
- Logo lockup centred at top of cover + back-cover slides only —
  never on body slides

**Slide types:**

| Type | Fill | Use |
|---|---|---|
| Cover | mustard full-bleed, ink frame inset | First and last slide of any deck |
| Research cover | teal full-bleed, ink frame inset | Methodology / appendix opening |
| Stage card | paper, rail variant | Body content |
| Editorial moment | paper, frame variant on mustard-pale | Big stat callouts, pull quotes |
| Divider | mustard-pale, frame variant, chip + chapter title centred | Between content groups |

Production helpers — use them, don't re-implement:

```python
# mmm_tool/export/vccp_brand.py
add_rect, add_text, add_rich_text, rail_border, frame_border,
solid_background, footer, source_caption, place_logo_centered,
add_highlight_text, stage_chip, stat_card
```

### The Frame & Patterns (VCCP corporate brand only)

Two elements unique to the corporate `VCCP` brand (not used in VCCP
Media collateral) — from `_VCCP Brand Guidelines_Dec 2025.pptx`.

**The Frame** — four logo-lockup frame types (Full Frame & Logo,
Girl & Bear Cinematic Frame, Cinematic Frame, Full Frame), available
in Mustard, Eggshell, Black or White.
- DO use the frame templates provided.
- DO NOT move the Girl & Bear off the position an approved template
  gives them, rescale or adjust the width of the frame, use more
  than one colour in it, or redraw it from scratch.

**Patterns** — four repeat patterns: VCCP Text, Girl & Bear, Stairway
1, Stairway 2. Default is the VCCP Text pattern.
- One colour family per instance only: Mustard tints on a Mustard
  background, Eggshell tints on an Eggshell background — **never
  mixed**.
- The "V" of the VCCP wordmark pattern must read top-left.
- DO NOT disproportionately scale a pattern, recolour it outside its
  family, overlay large blocks of text on top of one, or invent a
  new pattern. Opacity may be dialled up/down for subtlety.

### Writing rules

Two different registers, applied deliberately:

- **Titles / headlines** — written in the **WLV** (Write Like
  Vallance) voice: witty, erudite, one sharp metaphor or turn of
  phrase. Still **one sentence-case line** — WLV is normally a
  full-length thought-leadership voice, so compress it: the wit is
  in word choice, not in a run-on sentence. Call the `WLV` skill for
  the line itself, then drop it straight into the title placeholder.
- **Everything else** — body copy, bullets, captions, chart labels,
  source lines — is **British English, zero em/en dashes** (use
  commas, colons, brackets or full stops instead), **plain and
  analytical**, no hype language or rhetorical flourish. State the
  finding and the number. Prefer literal counts and named sources
  over any figure that is Claude's own interpretation dressed as a
  number.

Don't let the Vallance register bleed past the title into the body,
and don't let the body's plainness creep into the title — the
contrast (a memorable hook, then a sober analytical read) is the
point.

### PDF reports (typeset)

Two-column editorial layout, A4 portrait (210 × 297mm) for client
reports, A3 landscape (420 × 297mm) for foldout exec summaries.

- 0.6in margins minimum on A4, 0.8in on A3
- Inter Tight 10/14 body (10pt size, 14pt leading), 24pt headlines,
  72pt cover number callouts
- Mustard chips and frame cards survive at PDF size — soft shadow
  on `.vccp-card` does not, drop it
- Use **ReportLab** for programmatic generation (matches the deck
  builder pattern). Use **WeasyPrint** when you already have the
  HTML and want pixel-identical handoff
- Page-number convention: `01 / 24` bottom-right, letter-spaced
  caps, never `Page 1 of 24`

```python
# WeasyPrint embed of Inter Tight
from weasyprint import HTML, CSS
HTML(string=html).write_pdf(
    "report.pdf",
    stylesheets=[CSS(filename="vccp.css")],
    font_config=font_config,  # registered with InterTight-*.ttf
)
```

### PDFs from slides

Export PPTX → PDF via LibreOffice headless. Always check the result
for font substitution — if Inter Tight isn't installed on the
render host, the export silently falls back to a system sans and
ruins the brand.

```bash
soffice --headless --convert-to pdf deck.pptx
pdftoppm -jpeg -r 150 deck.pdf slide  # for visual QA
```

### Posters / out-of-home print

**Sizes:** A2 (420 × 594mm), A1 (594 × 841mm), 4-sheet (1016 ×
1524mm), 48-sheet (3048 × 6096mm).

- One headline, one highlighter, one supporting stat. Nothing else.
- Mustard or teal full-bleed background, ink frame inset 5% from
  edge, content inside the frame
- Headline size scales to roughly **20% of poster height** —
  generous, not timid
- Bleed: 3mm minimum, 5mm preferred. Crop marks on every export
- No imagery competing with the highlighter — if you have a photo,
  it goes inside the frame as a half-bleed strip, headline beside
  it on a mustard/teal flat ground

Production: build in InDesign or programmatically via ReportLab
with custom page size. Export PDF/X-1a for press.

### Infographics

Editorial layout, no chart-junk. The infographic *is* the chart —
no decorative borders, no shaded backgrounds, no 3D anything.

- Use **vccp_charts.py** matplotlib config as the base
- Title is sentence case with a highlighter accent on the key word
- Annotate series **inline** with `ax.text()` at the line endpoint —
  never use a boxed legend inside the plot area
- Mustard fill for the headline series; ink stroke; everything
  secondary in teal-deep or 40% grey
- Mustard-light area under the curve (alpha 0.55) when there's one
  series and you want emphasis
- Source caption 8.5pt grey, bottom-left

```python
import matplotlib as mpl
import matplotlib.pyplot as plt

VCCP_CYCLE = ['#FFC931', '#00BCA5', '#FF8812', '#80E8E3',
              '#000000', '#FFEDBB', '#BDF9F6']

mpl.rcParams.update({
    'font.family': 'Inter Tight',
    'font.size': 10,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.edgecolor': '#000000',
    'axes.linewidth': 1.0,
    'axes.titlesize': 14,
    'axes.titleweight': 500,
    'axes.labelsize': 10,
    'xtick.color': '#000000',
    'ytick.color': '#000000',
    'figure.facecolor': '#FFFFFF',
    'axes.facecolor': '#FFFFFF',
    'axes.prop_cycle': mpl.cycler(color=VCCP_CYCLE),
})
```

Chart types that fit the brand:

- Line + filled-area (one headline series, ≤2 secondary lines)
- Horizontal bar (mustard fill, ink stroke, value labels at bar end)
- Slope chart (two columns of data, mustard line for movers, grey for stayers)
- Sankey for budget reallocation (mustard from-flow, teal-deep into-flow)

Chart types that **don't** fit: pie charts, stacked area charts
with >3 categories, donut charts, 3D anything, word clouds.

### Social tiles

- **Square (1080 × 1080):** mustard full-bleed, ink frame inset
  60px, headline 88pt sentence case with one highlighter, supporting
  line 24pt
- **Story / portrait (1080 × 1920):** teal full-bleed if appendix /
  research, otherwise mustard; brand mark top-left, headline middle,
  swipe-up indicator bottom
- **Landscape (1200 × 630, OG / Twitter card):** as cover slide but
  cropped to 16:9 — headline left, supporting stat right inside a
  frame card

Never lose the highlighter — even at 1080 the parallelogram is the
recognition cue.

### Editorial / report covers

The frame card is doing the work here. Cover anatomy:

1. Mustard full-bleed (or teal for research)
2. Ink frame inset 5% from each edge
3. Inside the frame: eyebrow (date / version / division) top-left in
   letter-spaced caps
4. Centred headline 60–72pt sentence case, one highlighter on the
   verb or the main noun
5. Lede 16pt, ≤200 chars, left-aligned, below the headline with
   1.5x spacing
6. Brand mark bottom-right of frame, never centred unless it's a
   back cover

### Email signatures / business cards / collateral

- Mustard chip with the person's role in letter-spaced caps
- Square 1px ink border around any signature image
- Card stock: matt white 350gsm, single-side print, Pantone Yellow
  012 U (matches `#FFC931` on coated stock to ±0.5 ΔE)

---

## Buttons, forms, tables (web reference)

Full CSS lives in [`example.html`](example.html). Highlights:

```css
.vccp-table th, .vccp-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0,0,0,0.08);
}
.vccp-table th {
  text-align: left;
  font-size: 0.74rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-bottom: 1px solid var(--ink);
}
.vccp-table td.num { text-align: right; font-feature-settings: 'tnum'; }
.vccp-table tbody tr:hover { background: var(--mustard-pale); }

.vccp-delta-up    { color: var(--teal-deep); font-weight: 500; }
.vccp-delta-down  { color: var(--mustard-dark); font-weight: 500; }
```

Up-deltas in teal-deep, down-deltas in mustard-dark — both read as
"this number is moving" without using red/green. The brand has no
red/green system; don't invent one.

---

## Don'ts — common AI design mistakes

The single most common "this looks AI" tell is breaking one of
these rules. Re-read before declaring a draft done.

1. **Title Case headlines.** Sentence case only.
2. **Gradients.** The palette is flat. The only allowed soft is a
   barely-perceptible radial in `body::before` for very large web
   surfaces.
3. **Border-radius > 0** on cards, buttons, chips, frames. The nav
   pill is the only round element.
4. **Red/green colour system.** Up = teal-deep, down = mustard-dark.
5. **Icons inside the highlighter parallelogram.** Words only.
6. **Highlighting both verb and noun in one phrase.** One word per
   phrase, two per surface cover, never more.
7. **Anything other than Inter Tight.** Not Inter, not Tight Sans,
   not the variable axis. Specifically Inter Tight.
8. **Stretched or skewed brand mark.** Always proportional.
9. **Mustard text on teal background, or vice-versa.** Same value
   (≈75% luminance). Always pair with ink or paper.
10. **Mixing the two halves in one composition.** Pick mustard OR
    teal as the primary; the other appears only as a single accent
    or on a different surface in the same artifact.
11. **Pie charts, donut charts, stacked-areas with >3 categories.**
    Editorial brand → editorial chart types.
12. **Box-shadow on PDF cards.** It doesn't render the same and
    looks dirty at print resolution. Drop it for any output that's
    going through a PDF pipeline.
13. **A hand-drawn parallelogram with a guessed skew.** Duplicate an
    existing highlighter shape from the template; if you must build
    one, `adj = 0.25`, not any other value (see the dedicated section
    above — this was the single biggest source of off-brand decks).
14. **A highlighter spanning a full line or multiple lines.** One
    word or short phrase only.
15. **An outline on a highlighter shape, or the highlight sitting in
    front of its text.** No stroke, ever; sent to back, always.
16. **Vallance-voiced body copy, or a flat/analytical title.** The
    contrast between the two registers (see "Writing rules" above)
    is deliberate — don't collapse it either direction.
17. **An em dash or en dash anywhere in body copy.** Commas, colons,
    brackets or full stops instead.

---

## Quick-start templates

When generating a VCCP-branded artifact, Claude follows this order:

0. **Confirm which brand** — VCCP corporate or VCCP Media (default
   for anything client-facing) — and, for a deck, which gallery file
   fits the job (see "Slide decks" above).
1. **Pick the half** — mustard primary (default, operator-facing
   tools, hero collateral) or teal/eggshell primary (research,
   appendix, methodology, "premium/refined" moments). One per
   surface, never both full-bleed on the same page.
2. **Write the headline in the WLV voice** — one sentence-case line,
   period at the end, **one** verb or noun wrapped in
   `<em class="hl">` (web) or a duplicated highlighter parallelogram
   run (PPTX, `adj = 0.25`, no outline, sent to back) or a hand-set
   tilted fill (print). Never let the highlight span more than that
   one word/phrase.
3. **Write everything else — body, bullets, captions — in the plain
   analytical register**: British English, zero em/en dashes,
   literal numbers with named sources.
4. **Default to the rail card.** Reserve frame cards for hero /
   divider / "moment" surfaces.
5. **Stage-number chips for any numbered sequence** — 01, 02, 03
   in letter-spaced caps inside the mustard-with-ink-border chip.
6. **Tabular numerics** for every count/metric in every table or
   stat card.
7. **No round corners, no gradients, no red/green.**
8. **Footer with `© VCCP Media YYYY` + `page NN`** letter-spaced
   caps, bottom of every slide / page / poster.
9. **Source caption** (grey 8.5pt) bottom-left when external data
   is cited.

If unsure about a specific element, open `example.html` for the web
reference, or `mmm_tool/export/vccp_deck.build_pptx()` output for
the PPTX reference, and mirror what's there.

---

## Reference files in this skill

- [`SKILL.md`](SKILL.md) — this file
- [`example.html`](example.html) — full single-file web demo
  showing nav, cover, two-pane shell, rail + frame cards,
  highlighter (mustard + teal variants), stage chips, form fields,
  buttons, stat callouts, table with up/down deltas, footer
- [`references/pptx-template-population.md`](references/pptx-template-population.md)
  — the archetype-cloning method (never hand-draw on a blank
  `Presentation()`) plus the full marker-text index for every file
  in the gallery
- `~/Desktop/VCCP Templates/` — the full editable template gallery:
  `VCCP MEDIA/` (8 templates — Pitch, Strategy & Planning, Creds,
  Portrait A4, Ideas Book, Trump Card, SOAP & POAP, CIM Card) and
  `VCCP/_VCCP Brand Guidelines_Dec 2025.pptx` (the corporate brand
  source of truth — Frame, Patterns, colour/typography rules, the
  parallelogram highlighter rule). All `.pptx` — see "Do not" below
  for why other formats don't work with this method. **This is the
  canonical gallery** — if you're on a machine without it, ask the
  user for these files rather than trusting the legacy bundled asset
  below.
- [`assets/template/Media Template 2026 [Q2].pptx`](assets/template/Media%20Template%202026%20%5BQ2%5D.pptx)
  — **legacy, superseded.** Bundled here from an earlier version of
  the brand system; its archetype slide indices no longer match the
  current gallery (`Pitch Template 2026 [Q2].pptx` replaced it — see
  `references/pptx-template-population.md`). Kept only so the skill
  has *some* offline fallback on a machine with no access to
  `~/Desktop/VCCP Templates/`; don't use its slide indices as
  current, and prefer the real gallery whenever it's reachable. Not
  re-bundled with the full new gallery because the eight current
  templates total roughly 500MB, well past what a code repo (and
  GitHub's 100MB per-file limit) should carry — several of them
  individually exceed 100MB.

## Do not

- Download or re-export any gallery template as `.odp` or PDF. The
  cloning method (`Presentation(TEMPLATE)`, deep-copying real slide
  XML) is an OOXML operation — `python-pptx` cannot open `.odp` at
  all, and a PDF is flattened/non-editable. If a template only
  exists as a PDF, get the original editable file from whoever
  designed it rather than trying to populate the PDF directly.
- Invent a new `adj` value for the highlighter parallelogram, or
  draw one freehand from the shapes menu instead of duplicating an
  existing instance.
- Use the corporate Frame or Patterns on a VCCP Media artifact, or
  the rail/frame card vocabulary on a corporate VCCP artifact — they
  belong to different brand instances.

## Production reference (external repo)

The live production system: [`sebduffy-prog/MarketMixedModeller`](https://github.com/sebduffy-prog/MarketMixedModeller)

- `frontend/brand/vccp.css` — full web stylesheet
- `frontend/brand/vccp.js` — branded behaviour helpers
- `mmm_tool/export/vccp_brand.py` — PPTX primitives
- `mmm_tool/export/vccp_charts.py` — matplotlib rcParams config
- `mmm_tool/export/vccp_deck.py` — end-to-end deck construction
- `mmm_tool/export/fonts/` — bundled Inter Tight TTFs
