---
name: data-driven-deck-generator
category: documents
description: >-
  Generate a data-driven PowerPoint deck where every chart and headline is bound to real
  data — read a CSV/DataFrame/dict, build NATIVE editable python-pptx charts (column, bar,
  line, pie, stacked), apply a brand palette + fonts, auto-write insight titles from the
  numbers, and export a .pptx that opens clean in PowerPoint/Keynote/Google Slides. Reach
  for this when someone wants "turn this data into slides", a templated quarterly/KPI/pitch
  deck, or a repeatable report generator — not a one-off screenshot pasted into a slide.
when_to_use:
  - Turning a CSV / DataFrame / metrics dict into a multi-slide deck with editable charts
  - Building a repeatable templated report (quarterly, monthly KPI, campaign wrap) from data
  - Producing native PowerPoint charts a stakeholder can restyle or re-point, not flat images
  - Auto-generating insight-style slide titles and callouts computed from the numbers
  - Applying a fixed brand theme (palette, fonts, logo) across every generated slide
when_not_to_use:
  - You only need to read/parse or lightly edit an existing .pptx — use the `pptx` skill
  - The deliverable is a spreadsheet or the data model itself — use `xlsx` / `excel-*` skills
  - You want a purely visual poster/graphic with no data binding — use `canvas-design`
  - Choosing chart form, colour ramps, or accessibility rules — read `dataviz` first, then this
  - Building an interactive web dashboard rather than a file — use `frontend-design`
keywords:
  - powerpoint
  - pptx
  - python-pptx
  - deck
  - slides
  - chart
  - data-driven
  - report-generator
  - brand-theme
  - csv
  - dataframe
  - kpi
  - native-chart
  - templated-deck
  - export
similar_to:
  - pptx
  - dataviz
  - excel-kpi-dashboard-formulas
  - canvas-design
  - three-statement-financial-model
inputs_needed: >-
  Tabular data (CSV path / pandas DataFrame / list of dicts), a brand spec (hex palette +
  font names, optional logo PNG), and a slide plan (which metric maps to which chart type).
  Optional: a .pptx template file to inherit master/theme from.
produces: >-
  A single .pptx with native, editable charts bound to the data, brand-themed text and
  colours, computed insight titles, plus an optional Python generator script you can re-run
  when the data refreshes.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Data-Driven Deck Generator

Build a PowerPoint deck programmatically where charts are **native pptx chart objects**
(fully editable in PowerPoint, not pasted images) and every number, title, and colour is
driven from source data. Verified against `python-pptx` 1.0.2, Python 3.9.

## When to use

Someone hands you numbers ("here's the CSV, make the board deck") and wants slides that look
authored, stay on-brand, and can be regenerated when the data changes. This skill wires
data → charts → themed slides → `.pptx`. For chart *design decisions* (which chart, colour
ramp, accessible contrast) read the `dataviz` skill first — it defines the visual system;
this skill implements it in pptx.

## Prerequisites

```bash
python3 -m pip install python-pptx     # 1.0.x; pulls in lxml, Pillow, XlsxWriter
python3 -m pip install pandas          # optional, only if ingesting CSV/Excel
```
No LibreOffice/brew needed. Fonts referenced by name must exist on the *viewer's* machine
(embed only via PowerPoint itself). Use widely available families or the brand's licensed font.

## Core model (read once)

- A deck is `Presentation()`. Set 16:9 with `slide_width = Inches(13.333)`, `height = Inches(7.5)`.
- Build slides on the **blank** layout (`prs.slide_layouts[6]`) so you control every shape.
- A native chart = `shapes.add_chart(XL_CHART_TYPE.X, x, y, cx, cy, chart_data)`.
- `CategoryChartData`: `.categories = [...]`; one `.add_series(name, (values...))` per series.
- Colour **multi-series** per series (`chart.series[i].format.fill`); colour **single-series**
  pie/bar per point (`plot.series[0].points[i].format.fill`). Refresh via `chart.replace_data(cd)`.
- Number formats need `number_format_is_linked = False` or PowerPoint ignores your format.

## Recipe 1 — Themed clustered-column slide from data

```python
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION

# --- brand spec (edit these) ---
INK   = RGBColor(0x1A, 0x1A, 0x2E)          # headings / axis text
SERIES = [RGBColor(0x1A,0x1A,0x2E), RGBColor(0xE4,0x3D,0x5A), RGBColor(0x16,0xC7,0x9E)]
FONT  = "Arial"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
slide = prs.slides.add_slide(prs.slide_layouts[6])

cd = CategoryChartData()
cd.categories = ["Q1", "Q2", "Q3", "Q4"]
cd.add_series("2025", (18.2, 22.7, 25.1, 29.4))
cd.add_series("2026", (21.0, 24.3, 28.9, 34.1))

gf = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    Inches(0.7), Inches(1.6), Inches(11.9), Inches(5.2), cd)
chart = gf.chart
chart.has_title = False                     # use a real textbox title instead (below)
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
chart.legend.include_in_layout = False
chart.legend.font.size = Pt(12); chart.legend.font.name = FONT

plot = chart.plots[0]
plot.gap_width = 80                          # tighter bars read better
plot.has_data_labels = True
plot.data_labels.number_format = "0.0"
plot.data_labels.number_format_is_linked = False
plot.data_labels.font.size = Pt(10); plot.data_labels.font.name = FONT

for i, ser in enumerate(chart.series):       # brand colour per series
    ser.format.fill.solid()
    ser.format.fill.fore_color.rgb = SERIES[i % len(SERIES)]

va = chart.value_axis
va.has_major_gridlines = True
va.tick_labels.number_format = "0"; va.tick_labels.number_format_is_linked = False
va.tick_labels.font.size = Pt(11); va.tick_labels.font.name = FONT
chart.category_axis.has_major_gridlines = False
chart.category_axis.tick_labels.font.size = Pt(12)

prs.save("deck.pptx")
```

## Recipe 2 — Computed insight title (data drives the words)

Never hand-type "Revenue up". Let the data write the headline, so a re-run stays truthful.

```python
def insight_title(label, curr, prev, unit="%"):
    delta = curr - prev
    pct = (delta / prev * 100) if prev else 0
    dir_ = "up" if delta >= 0 else "down"
    return f"{label} {dir_} {abs(pct):.0f}% to {curr:.1f}{unit}"

def add_title(slide, text, ink, font, sub=None):
    tb = slide.shapes.add_textbox(Inches(0.7), Inches(0.45), Inches(11.9), Inches(1.05))
    tf = tb.text_frame; tf.word_wrap = True
    r = tf.paragraphs[0].add_run(); r.text = text
    r.font.size = Pt(30); r.font.bold = True; r.font.name = font; r.font.color.rgb = ink
    if sub:
        p = tf.add_paragraph(); s = p.add_run(); s.text = sub
        s.font.size = Pt(14); s.font.name = font
        s.font.color.rgb = RGBColor(0x6B, 0x6B, 0x7B)

add_title(slide, insight_title("FY revenue", 34.1, 29.4, "m"), INK, FONT,
          sub="Source: finance ledger, pulled 2026-07-09")
```

## Recipe 3 — Single-series pie/bar, coloured per point

```python
from pptx.enum.chart import XL_LABEL_POSITION
cd = CategoryChartData()
cd.categories = ["Organic", "Paid", "Referral"]
cd.add_series("share", (45, 33, 22))
gf = slide.shapes.add_chart(XL_CHART_TYPE.PIE, Inches(3.5),Inches(1.6),Inches(6.3),Inches(5.2), cd)
plot = gf.chart.plots[0]
plot.has_data_labels = True
plot.data_labels.show_percentage = True
plot.data_labels.number_format = "0%"; plot.data_labels.number_format_is_linked = False
plot.data_labels.position = XL_LABEL_POSITION.OUTSIDE_END
gf.chart.has_legend = True
for i, point in enumerate(plot.series[0].points):
    point.format.fill.solid()
    point.format.fill.fore_color.rgb = SERIES[i % len(SERIES)]
```

## Recipe 4 — Ingest a CSV and fan out a slide per metric

```python
import pandas as pd
df = pd.read_csv("metrics.csv")              # cols: period, revenue, users, margin
def bind_series(cd, df, cols):
    cd.categories = list(df["period"])
    for c in cols:
        cd.add_series(c.title(), tuple(df[c]))
    return cd

for metric, ctype in [("revenue", XL_CHART_TYPE.COLUMN_CLUSTERED),
                      ("users",   XL_CHART_TYPE.LINE_MARKERS)]:
    s = prs.slides.add_slide(prs.slide_layouts[6])
    cd = bind_series(CategoryChartData(), df, [metric])
    s.shapes.add_chart(ctype, Inches(0.7),Inches(1.6),Inches(11.9),Inches(5.2), cd)
    add_title(s, insight_title(metric.title(),
              float(df[metric].iloc[-1]), float(df[metric].iloc[0])), INK, FONT)
```

Validate the DataFrame at the boundary before binding: assert required columns exist, coerce
numerics (`pd.to_numeric(df[c], errors="raise")`), and fail fast with a clear message — a
silent `NaN` becomes an empty bar with no error.

## Recipe 5 — Inherit a brand template

To pick up a client master/theme (logo, colours, fonts) instead of the default:
```python
prs = Presentation("brand_template.pptx")    # keep its slide masters & theme
# then add_slide on its layouts; add_chart still yields native, editable charts
```
Drop a logo per slide with `slide.shapes.add_picture("logo.png", Inches(11.4), Inches(0.4), height=Inches(0.6))`.

## Chart-type cheat sheet (`XL_CHART_TYPE`)

| Intent | Member |
|---|---|
| Compare categories | `COLUMN_CLUSTERED`, `BAR_CLUSTERED` |
| Part-to-whole over time | `COLUMN_STACKED`, `COLUMN_STACKED_100` |
| Trend | `LINE`, `LINE_MARKERS` |
| Composition (few slices) | `PIE`, `DOUGHNUT` |
| Correlation | `XY_SCATTER` (use `XyChartData`, not `CategoryChartData`) |

## Verify

1. `python3 your_generator.py` writes the file with no traceback.
2. Sanity-check structure headlessly:
   ```bash
   python3 -c "from pptx import Presentation; p=Presentation('deck.pptx'); \
   print('slides', len(p.slides._sldIdLst)); \
   print('charts', sum(1 for s in p.slides for sh in s.shapes if sh.has_chart))"
   ```
3. Open in PowerPoint/Keynote: click a chart → **Edit Data** shows the real numbers (proves it's
   native, not an image). On this Mac, render-QA via `python-pptx` geometry only — there is no
   LibreOffice/`soffice` to convert to PDF (see office render limitation).

## Pitfalls

- **Number formats ignored.** Always set `number_format_is_linked = False` alongside any
  `number_format`, or PowerPoint reverts to the source-linked format.
- **Colouring the wrong level.** Multi-series → colour `chart.series[i]`. Single-series pie/bar
  looks monochrome unless you colour each `plot.series[0].points[i]`.
- **`has_title = True` fights your textbox.** Prefer `chart.has_title = False` + a real textbox
  title so you control font, wrap, and the computed insight string.
- **Emoji/glyph gaps.** A font missing a glyph renders tofu on the viewer's machine; stick to
  the brand family and avoid emoji in titles.
- **Fabricated numbers.** If data is missing, scaffold the slide with an explicit "awaiting
  data" placeholder — never invent values to fill a chart.
- **Scatter needs `XyChartData`.** `CategoryChartData` silently mis-plots XY; import the right
  data class for `XY_SCATTER`/`BUBBLE`. Every series tuple must also match the category count,
  or the last bars go blank with no exception raised.
- **Overwriting a template's masters.** Opening `Presentation("template.pptx")` inherits its
  theme; adding your own masters or deleting layouts can strip the brand — add slides onto the
  existing layouts instead.
