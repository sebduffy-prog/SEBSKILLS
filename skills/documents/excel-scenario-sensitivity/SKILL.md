---
name: excel-scenario-sensitivity
category: documents
description: >-
  Build deterministic what-if analysis in a real .xlsx — native one- and two-variable
  Data Tables (Excel's {=TABLE()} array via openpyxl DataTableFormula), CHOOSE/SWITCH
  scenario toggles, tornado sensitivity charts, and closed-form break-even. Use when a
  model needs Base/Bull/Bear cases, a profit-by-price-x-volume grid, "which input moves
  the answer most", or break-even units/revenue — all as live formulas, nothing baked in.
when_to_use:
  - Adding Base/Bull/Bear (or best/worst) scenario switching to an existing Excel model
  - Building a one- or two-variable Data Table (sensitivity grid) that recalculates in Excel
  - Ranking drivers by impact with a tornado chart before a decision or board pack
  - Solving break-even units/revenue, or a margin-of-safety, in closed form
  - Turning a Goal-Seek / manual what-if habit into a reproducible generated workbook
when_not_to_use:
  - Building the underlying P&L/BS/CF itself — use three-statement-financial-model first
  - Valuation cases (WACC x growth sensitivity on enterprise value) — use dcf-lbo-valuation-model
  - Randomised / probabilistic simulation (Monte Carlo, distributions) — Data Tables are deterministic; script the trials in xlsx
  - Reusable custom sensitivity functions — use excel-lambda-functions
  - Auditing/tracing an existing model's precedents and errors — use excel-model-audit
keywords:
  - data table
  - what-if analysis
  - sensitivity
  - scenario
  - two-variable
  - tornado
  - break-even
  - choose
  - switch
  - goal seek
  - openpyxl
  - datatableformula
  - deterministic
  - excel
similar_to:
  - three-statement-financial-model
  - dcf-lbo-valuation-model
  - excel-lambda-functions
  - excel-dynamic-array-formulas
  - excel-model-audit
inputs_needed: A model whose output is a formula of a few named driver cells (or use the bundled demo). For Data Tables you must know which single cell is the row input and which is the column input.
produces: A .xlsx with a CHOOSE/SWITCH scenario selector, native 1-var and 2-var Data Tables, a tornado table + horizontal bar chart, and break-even outputs — every result a live Excel formula.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel Scenario & Sensitivity Analysis

Deterministic what-if in a native `.xlsx`: flip scenarios with one cell, sweep one or two
inputs across a grid that Excel recalculates, rank drivers with a tornado, and solve
break-even in closed form. Generated with `openpyxl` — reproducible, no manual clicking.

## When to use

You already have (or will scaffold) a model where the answer is a formula of a handful of
driver cells, and you want the *classic* what-if toolkit around it. This skill is the
sensitivity layer; build the model itself with the sibling model skills.

## Prerequisites

- macOS `python3` (3.9) with `openpyxl` 3.1+ (`python3 -c "import openpyxl,sys;print(openpyxl.__version__)"`).
- The model output must reference **cells**, not literals — a Data Table works by
  substituting values into the row/column *input cell*, so the output must depend on it.
- Data Tables recompute **only inside Excel**. `openpyxl` never evaluates them; the file
  ships with `fullCalcOnLoad` so Excel fills the grid on first open. LibreOffice recalcs
  Data Tables too (Tools ▸ Cell Contents ▸ Recalculate / Ctrl+Shift+F9).

## Recipes

### 1. Generate the worked example

```bash
python3 scripts/build_scenario.py out.xlsx   # scenario toggle + 2 Data Tables + tornado + break-even
```

Open in Excel, change `B1` (1/2/3) to flip Base/Bull/Bear, and watch every output move.
Adapt the driver values and the output formula (`PROFIT`) to your own model.

### 2. Scenario toggle — CHOOSE (universal) vs SWITCH (2019/365)

Lay driver scenarios in adjacent columns and drive an **Active** column off one selector
cell. `CHOOSE(index, …)` works in every Excel version and needs contiguous 1..N indices:

```
B1 = 2                              ' 1=Base 2=Bull 3=Bear
B5 = CHOOSE($B$1, C5, D5, E5)       ' Active Price picks the Bull column
```

`SWITCH` is clearer for non-contiguous / labelled keys but is **Excel 2019+ / 365 only**
(it silently `#NAME?`s in 2016 and earlier):

```
B5 = SWITCH($B$1, 1, C5, 2, D5, 3, E5)
B5 = SWITCH($C$1, "Base", C5, "Bull", D5, "Bear", E5, C5)   ' last arg = default
```

Point the whole model at the Active column. One cell now reshapes the entire workbook.

### 3. Native two-variable Data Table (the real `{=TABLE()}`)

A two-variable table is: a corner cell linking to the output, the **row input's** values
across the top, the **column input's** values down the left, and a body of the `TABLE`
array. In OOXML the master body cell carries `<f t="dataTable" dt2D="1" r1=… r2=…>` where
**`r1` = row input cell** (top-row values) and **`r2` = column input cell** (left values):

```python
from openpyxl.worksheet.formula import DataTableFormula
ws["G22"] = "=B15"                      # corner = link to the Profit output
# H22:L22 = Price values (top)  ->  fed into row input cell B5
# G23:G28 = Units values (left) ->  fed into column input cell B4
ws["H23"] = DataTableFormula(ref="H23:L28", dt2D=True, r1="B5", r2="B4", ca=True)
```

Write the array to its **master (top-left body) cell only**; `ref` spans the whole body
and Excel fills the rest. `ca=True` marks it dirty so it recalcs on open.

### 4. Native one-variable Data Table

Input values down a column, the output formula one row up and one column right of them.
Column-oriented ⇒ `dt2D=False, dtr=False`, single input cell in `r1`:

```python
ws["H31"] = "=B15"                                  # output formula, above the body
# G32:G37 = Price values to test (column input)
ws["H32"] = DataTableFormula(ref="H32:H37", dt2D=False, dtr=False, r1="B5", ca=True)
```

For a **row-oriented** one-variable table (values across a row instead), set `dtr=True`
and keep `r1` as the single input cell; the output formula sits one column left and one row
down of the input row.

Doing it by hand in Excel: select the block (values + formula), **Data ▸ What-If Analysis
▸ Data Table**, and fill only the matching input box (Column input for a column of values,
Row input for a row). Never type `=TABLE(...)` yourself — Excel refuses it.

### 5. Tornado sensitivity

Perturb each driver ±X% around the Base case, holding the others fixed, and record the
profit at each extreme. `Swing = ABS(High − Low)`; **sort descending** for the classic
funnel. Because the output is a formula of the Base cells, each leg is closed-form — no
Data Table needed per driver:

```
Units  Low  =(C4*0.8)*(C5-C6)-C7      High =(C4*1.2)*(C5-C6)-C7
Price  Low  =C4*((C5*0.8)-C6)-C7      High =C4*((C5*1.2)-C6)-C7
VarCost Low =C4*(C5-(C6*1.2))-C7      High =C4*(C5-(C6*0.8))-C7   ' cost UP => profit DOWN
Fixed  Low  =C4*(C5-C6)-(C7*1.2)      High =C4*(C5-C6)-(C7*0.8)
```

Plot `Swing` as a horizontal bar (`BarChart(type="bar")`) for the visual tornado.

### 6. Break-even & margin of safety

Contribution margin makes break-even closed-form — prefer it over iterative Goal Seek:

```
CM per unit      = Price - VarCost                       ' = B5-B6
Break-even units = FixedCost / (Price - VarCost)         ' guard: =IFERROR(...,NA())
Break-even rev   = BE_units * Price
Margin of safety = (Actual_units - BE_units) / Actual_units
```

Guard the divide (`IFERROR`) so `Price = VarCost` shows `#N/A`, not a silent giant number.
For outputs with no clean algebra, Excel **Goal Seek** (Data ▸ What-If Analysis) solves one
input for a target — but it mutates the input cell in place and isn't reproducible, so it's
a spreadsheet action, not something `openpyxl` can bake in.

## Verify

```bash
python3 scripts/build_scenario.py check.xlsx
python3 - <<'PY'
import zipfile, re, openpyxl
z = zipfile.ZipFile("check.xlsx"); xml = z.read("xl/worksheets/sheet1.xml").decode()
assert re.search(r'<f t="dataTable"[^>]*dt2D="1"[^>]*r1="B5"[^>]*r2="B4"', xml), "2-var table missing"
assert re.search(r'<f t="dataTable" ref="H32:H37"[^>]*r1="B5"', xml), "1-var table missing"
assert "CHOOSE($B$1" in xml and "SWITCH($B$1" in xml, "scenario toggles missing"
assert openpyxl.load_workbook("check.xlsx").calculation.fullCalcOnLoad, "fullCalcOnLoad off"
print("OK: native Data Tables + toggles present, recalc-on-open armed")
PY
```

Then open in Excel: change `B1` and confirm the outputs, both Data Table grids, and the
tornado all move. If a Data Table body shows only the corner value, force recalc (Ctrl/⌘+=,
or `Ctrl+Alt+F9`) — a `.xlsx` written by tooling may not auto-fill until a full calc runs.

## Pitfalls

- **`openpyxl` can't compute Data Tables.** Reading the file back in Python shows blank body
  cells — that's expected. Only Excel/LibreOffice fill them. Never assert on their *values*
  in a Python test; assert on the `dataTable` XML instead (see Verify).
- **`r1`/`r2` swapped** silently transposes the grid. `r1` = **row** input (top values),
  `r2` = **column** input (left values). Mixing them up is the #1 Data Table bug.
- **Master cell only.** Put the `DataTableFormula` on the top-left body cell with a `ref`
  spanning the whole body. Writing it into every cell, or onto the header/corner, corrupts
  the array in Excel.
- **`SWITCH` in old Excel** returns `#NAME?`. If the file may open in 2016 or earlier, use
  `CHOOSE` (contiguous index) or nested `IF`.
- **Volatile inputs (`RAND`, `NOW`, `OFFSET`) inside a Data Table** re-roll on every table
  pass, so the labels no longer match the results. Freeze them, or scan a static column.
- **Whole-column / whole-sheet Data Tables are slow** — Excel recalcs the model once per
  body cell. Keep grids small and consider Calculation ▸ *Automatic Except Data Tables*.
- **Break-even divide-by-zero.** Always wrap `FixedCost/(Price−VarCost)` in `IFERROR`.
- **Tornado sign for costs.** A cost rising cuts profit, so the cost driver's *Low-profit*
  leg uses the *high* cost multiplier. Getting this backwards inverts the bar.
