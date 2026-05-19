---
name: vccp-media-design
description: |
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

---

## TL;DR — the five rules

1. **Pick one half.** Mustard is the primary surface for operator-
   facing / hero / cover artifacts. Teal is the appendix half:
   research, methodology, supporting material. Never split a single
   composition 50/50 between them.
2. **Sentence case, Inter Tight, all weights 300–700.** No serifs,
   no monospace pairings, no Title Case headlines.
3. **The highlighter parallelogram** (`skewX(-12deg)` mustard-light
   box behind one italic accent word) is the single recurring motif.
   One per phrase, max two per surface.
4. **Square corners, no gradients, no rounded buttons.** Editorial,
   not SaaS. The only rounded element is the nav pill.
5. **Tabular numbers, ink-on-paper or paper-on-ink for contrast.**
   No red/green deltas — up is `--teal-deep`, down is `--mustard-dark`.

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

The single most distinctive element. A mustard-light box behind one
italic accent word, sheared `skewX(-12deg)` to match the italic
slant. This is what "looks VCCP" at a glance.

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
- Mustard highlighter on a mustard surface → invisible. Use
  `.hl-teal` variant or invert to ink-on-paper for the whole text

**For PPTX**: the highlighter is a `MSO_SHAPE.PARALLELOGRAM` filled
with `MUSTARD_LITE`, no border, behind a transparent text frame.
Skew comes from the shape's `adjustments[0] = 0.08` (≈ -12 deg
shear). See `mmm_tool/export/vccp_brand.py::add_highlight_text()`.

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

Widescreen 16:9 at **11.811" × 6.646"** (matches the Media Template
2026 master used in PowerPoint UK).

```python
from pptx.util import Inches
SLIDE_W = Inches(11.811)
SLIDE_H = Inches(6.646)
```

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

---

## Quick-start templates

When generating a VCCP-branded artifact, Claude follows this order:

1. **Pick the half** — mustard primary (default, operator-facing
   tools, hero collateral) or teal primary (research, appendix,
   methodology). One per surface.
2. **Write the headline as a sentence**, ending in a period, with
   **one** verb or noun wrapped in `<em class="hl">` (web) or an
   italic-with-parallelogram run (PPTX) or a hand-set tilted fill
   (print).
3. **Default to the rail card.** Reserve frame cards for hero /
   divider / "moment" surfaces.
4. **Stage-number chips for any numbered sequence** — 01, 02, 03
   in letter-spaced caps inside the mustard-with-ink-border chip.
5. **Tabular numerics** for every count/metric in every table or
   stat card.
6. **No round corners, no gradients, no red/green.**
7. **Footer with `© VCCP Media YYYY` + `page NN`** letter-spaced
   caps, bottom of every slide / page / poster.
8. **Source caption** (grey 8.5pt) bottom-left when external data
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

## Production reference (external repo)

The live production system: [`sebduffy-prog/MarketMixedModeller`](https://github.com/sebduffy-prog/MarketMixedModeller)

- `frontend/brand/vccp.css` — full web stylesheet
- `frontend/brand/vccp.js` — branded behaviour helpers
- `mmm_tool/export/vccp_brand.py` — PPTX primitives
- `mmm_tool/export/vccp_charts.py` — matplotlib rcParams config
- `mmm_tool/export/vccp_deck.py` — end-to-end deck construction
- `mmm_tool/export/fonts/` — bundled Inter Tight TTFs
