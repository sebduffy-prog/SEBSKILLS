---
name: excel-kpi-dashboard-formulas
category: documents
description: >-
  Build a single-screen, formula-driven KPI dashboard in Excel with zero VBA or macros — a
  SWITCH/CHOOSE metric selector wired to a dropdown, spilled summary blocks (FILTER + GROUPBY),
  in-cell REPT bar charts, delta-vs-target and RAG status formulas, and native Conditional
  Formatting (data bars, icon sets, colour scales). Reach for this when a stakeholder wants a
  live "pick a metric / period and everything updates" report that stays refresh-free, printable,
  and safe to email — Chandoo-style dashboards without a single line of code.
when_to_use:
  - Turning a flat data Table into a one-screen dashboard where a dropdown drives every tile
  - Building KPI cards showing actual vs target vs prior with a coloured up/down delta
  - Adding in-cell bar charts or spark-bars next to a list without inserting chart objects
  - Applying data bars / icon sets / colour scales to rank or RAG-status a metric column
  - Producing a macro-free, VBA-free dashboard that survives being emailed or opened read-only
when_not_to_use:
  - You need the underlying spilling-formula toolkit itself — use `excel-dynamic-array-formulas`
  - Wrapping repeated dashboard logic into one named function — use `excel-lambda-functions`
  - Building a P&L / balance-sheet / cash-flow engine — use `three-statement-financial-model`
  - What-if input grids and tornado sensitivity — use `excel-scenario-sensitivity`
  - Generating the .xlsx programmatically from data — use the `xlsx` skill (openpyxl)
keywords:
  - excel
  - dashboard
  - kpi
  - switch
  - choose
  - rept
  - in-cell-bar
  - conditional-formatting
  - data-bars
  - icon-sets
  - sparkline
  - data-validation
  - dropdown
  - rag-status
  - delta
  - chandoo
  - no-vba
  - office365
similar_to:
  - excel-dynamic-array-formulas
  - excel-lambda-functions
  - excel-scenario-sensitivity
  - three-statement-financial-model
inputs_needed: A tabular range or structured Table (metric, period, actual, target, prior columns typical) in Excel 365 or 2021+; a blank sheet for the dashboard tab.
produces: A single-screen, formula-only KPI dashboard — dropdown-driven selectors, spilled summaries, in-cell bars, delta/RAG cells, and Conditional Formatting — with no VBA or macros.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel KPI Dashboard Formulas

A good dashboard is one screen, updates the instant a dropdown changes, and contains **no code**
— so it opens clean in protected view, prints to one page, and is safe to email. This skill wires
a flat data Table to selector-driven KPI tiles using SWITCH/CHOOSE, spilling summaries, REPT
in-cell bars, and native Conditional Formatting. Keep it a `.xlsx`, never `.xlsm`.

## When to use

Use when someone asks for a "live report where I pick a metric/region/month and everything
updates". If the instinct is a macro button or a rebuilt PivotChart on every refresh — stop and
drive it with a dropdown + formulas instead.

## Prerequisites

- **Version**: SWITCH, IFS, XLOOKUP, TEXTJOIN, CHOOSE, REPT are in Excel 2019+. The spilling
  summary blocks (FILTER, GROUPBY) need Microsoft 365 / 2021+. Sparklines (Insert > Sparklines)
  and Conditional Formatting are native everywhere from 2010.
- **Layout**: keep three tabs — `Data` (the source Table), `Calc` (helper/staging formulas),
  `Dashboard` (the presentation grid). Never format directly on raw data.
- **Source shape**: one contiguous Table (`Ctrl+T`, name it `tbl`). Long/tidy format
  (one row per metric×period) drives selectors far more cleanly than wide format.

## Recipe 1 — the metric selector (dropdown → live value)

Build the dropdown with Data Validation, then translate the choice with SWITCH or, for a
positional pick, CHOOSE.

```
1. On Dashboard!B2 add the dropdown:
   Data > Data Validation > Allow: List >
   Source:  =SORT(UNIQUE(tbl[Metric]))      (spill the list on Calc, point Source at it)

2. Translate the chosen label to a column/aggregate with SWITCH:
   =SWITCH($B$2,
      "Revenue",  SUM(tbl[Revenue]),
      "Margin %", AVERAGE(tbl[Margin]),
      "Orders",   SUM(tbl[Orders]),
      NA())                                  ← final arg = default, use NA() to flag typos
```

CHOOSE is the positional cousin — pair it with `MATCH` when the dropdown index maps to columns:

```
=CHOOSE(MATCH($B$2, {"Revenue","Margin %","Orders"}, 0),
        SUM(tbl[Revenue]), AVERAGE(tbl[Margin]), SUM(tbl[Orders]))
```

Prefer **SWITCH** for readability (label→result pairs); use CHOOSE only when you already
have a clean 1..n index. Add a **period** dropdown the same way and combine both in the
summary block below.

## Recipe 2 — spilled summary block (one formula, many rows)

The body of the dashboard is a single FILTER (or GROUPBY) that reacts to both dropdowns.

```
Rows for the chosen metric, newest first:
=SORT(FILTER(tbl[[Period]:[Actual]],
             (tbl[Metric]=$B$2)*(tbl[Region]=$B$3), "no data"),
      1, -1)

Group actuals by region for the chosen metric (365):
=GROUPBY(FILTER(tbl[Region], tbl[Metric]=$B$2),
         FILTER(tbl[Actual], tbl[Metric]=$B$2),
         SUM, , 0, -2)          ← 6th arg -2 = sort by aggregate descending
```

Always pass FILTER's 3rd `if_empty` arg (`"no data"`, `0`) or an empty filter returns `#CALC!`.
Reference the spill downstream with the `#` anchor, e.g. `=ROWS(E5#)` counts the live rows.

## Recipe 3 — KPI tile: actual vs target vs prior

Each card is a small block of scalar formulas. Compute the delta and a signed % once, then
format the sign visually (Recipe 5), not with red text baked into the formula.

```
Actual   =SUMIFS(tbl[Actual], tbl[Metric],$B$2, tbl[Period],$B$4)
Target   =SUMIFS(tbl[Target], tbl[Metric],$B$2, tbl[Period],$B$4)
Prior    =SUMIFS(tbl[Actual], tbl[Metric],$B$2, tbl[Period],$B$4-1)

Δ vs target   =[Actual]-[Target]
% vs target   =IFERROR([Actual]/[Target]-1, "n/a")
Arrow label   =IF(Actual>=Target,"▲","▼")&" "&TEXT(%vsTarget,"+0.0%;-0.0%")
RAG status    =IFS(Actual>=Target,"On track",
                   Actual>=Target*0.9,"At risk",
                   TRUE,"Off track")
```

Format the % cell with a custom number format so the sign colours itself, no formula branch:
`[Green]+0.0%;[Red]-0.0%;0.0%`.

## Recipe 4 — in-cell bar charts with REPT

REPT draws a bar from a block glyph, scaled to the row's share of the column max. This needs no
chart object and prints perfectly.

```
Bar (fixed 20-char width):
=REPT("█", ROUND(20*[@Actual]/MAX(tbl[Actual]), 0))

Two-tone actual-vs-target overlay (bar + remaining track):
=REPT("█", ROUND(20*[@Actual]/[@Target],0)) & REPT("░", 20-ROUND(20*[@Actual]/[@Target],0))
```

Set the cell font to a fixed-pitch font (Consolas) and left-align so bars line up. For a
proper mini line/column trend inside one cell use native **Sparklines** (Insert > Sparklines >
Line/Column/Win-Loss) — those are cell-embedded charts, not a formula, and update with the data.

## Recipe 5 — Conditional Formatting (data bars, icon sets, colour scales)

Do the visual RAG work with native Conditional Formatting rules, not colour typed into cells —
rules recalc live and survive sorting.

```
Data bars:    select the Actual column > Home > Conditional Formatting > Data Bars.
              Tick "Show Bar Only" to hide numbers for a pure bar column.
Colour scale: 3-colour scale on the %-vs-target column (red-yellow-green).
Icon sets:    3-arrows / traffic-lights on the RAG cell.
              Rule type "Number", not "Percent": Green ≥ 1, Yellow ≥ 0.9, else Red.
Formula rule: highlight whole row when off track >
              =$G5="Off track"   (apply to the row range, lock the column with $).
```

Anchor Data-Validation dropdowns and CF ranges to the Table so they extend as data grows;
CF applied to a Table column auto-expands with new rows.

## Verify

1. Change each dropdown — every tile, spill block, bar and CF colour must update with **zero**
   manual refresh. If a tile is static, it's referencing a cell not the selector.
2. Add a row to `tbl`; the spilled summary should grow and CF/data-bars should cover it.
3. Save as `.xlsx` and reopen — no "enable macros" banner should appear (proves it's code-free).
4. `Ctrl+P` preview: the dashboard should fit one page. Scan for `#SPILL!`, `#CALC!`, `#N/A`.
5. Type a nonsense label into a dropdown-linked cell — SWITCH's `NA()` default should surface
   `#N/A` rather than silently returning a wrong number.

## Pitfalls

- **`.xlsm` creep** — the whole point is macro-free; if the file became `.xlsm`, resave as
  `.xlsx`. Any dashboard needing VBA has failed this skill's brief.
- **`#SPILL!` under a summary block** — cells below/right of a FILTER/GROUPBY anchor must be
  empty. Don't place a KPI tile in the spill's growth path; leave a clear gutter.
- **REPT overflow** — REPT caps at 32,767 characters but a bar of 200 glyphs is unreadable;
  keep the scale factor ~10–25 and always divide by `MAX(...)` so the longest bar fits.
- **Icon-set rule type** — Excel defaults new icon-set thresholds to *Percent* (of range), which
  breaks RAG logic; switch each threshold to *Number* and enter the literal cutoffs.
- **Volatile selectors** — avoid `OFFSET`/`INDIRECT` to build the dropdown source; they don't
  auto-resize predictably and recalc on every edit. Use `SORT(UNIQUE(tbl[Col]))` spilled instead.
- **CF colour ≠ data** — Conditional Formatting is display-only; a filter or another formula
  can't read a cell's fill. If downstream logic needs the status, keep the RAG **text** formula
  (Recipe 3) as the source of truth and colour it separately.
- **Merged cells** — merging tile headers breaks spill ranges and sort; use "Center Across
  Selection" (Format Cells > Alignment) for the same look without the merge.
- **Hard-coded period math** — `$B$4-1` for "prior" assumes numeric periods; for month labels
  build a proper period index column in `Data` and look up prior via `XLOOKUP`/`MATCH-1`.
