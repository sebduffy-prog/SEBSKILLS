---
name: excel-dynamic-array-formulas
category: documents
description: >
  Replace VLOOKUP-drag, helper columns, and manual pivot tables with spilling dynamic-array
  formulas — FILTER, SORT, SORTBY, UNIQUE, SEQUENCE, XLOOKUP/XMATCH, plus the modern GROUPBY
  and PIVOTBY aggregators. Reach for this whenever a report re-drags formulas down every time
  data grows, uses index/match gymnastics, hard-codes ranges, or needs a live pivot that
  recalculates without refresh. Turns brittle grids into single self-resizing formulas.
when_to_use:
  - Building a report that must auto-resize as rows are added, without dragging formulas
  - Replacing VLOOKUP/INDEX-MATCH helper columns with one spilling formula
  - Producing a live grouped summary (sum/avg/count by category) that recalcs instantly
  - Extracting a distinct list, a filtered subset, or a top-N ranking with a formula
  - Cross-tabulating (rows x columns) without inserting a PivotTable object
when_not_to_use:
  - Deliverable is a .xlsx you generate programmatically — use `xlsx` (openpyxl writes values/formulas)
  - Building a full financial model structure — use `three-statement-financial-model` or `dcf-lbo-valuation-model`
  - Wrapping reusable custom logic into a named function — use `excel-lambda-functions`
  - Auditing an existing workbook for errors/dependencies — use `excel-model-audit`
keywords:
  - excel
  - dynamic-array
  - spill
  - filter
  - sort
  - unique
  - sequence
  - xlookup
  - groupby
  - pivotby
  - textsplit
  - spill-range
  - hstack
  - formula
  - office365
similar_to:
  - excel-lambda-functions
  - excel-scenario-sensitivity
  - excel-model-audit
  - excel-kpi-dashboard-formulas
inputs_needed: A tabular range/Table in Excel 365 or Excel 2024+ (dynamic arrays required); column layout of source data.
produces: Spilling dynamic-array formulas that self-resize, replacing dragged formulas, helper columns, and static pivots.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel Dynamic-Array Formulas

Modern Excel (Microsoft 365 and Excel 2021/2024+) evaluates a single formula into a **spill
range** — many cells filled from one anchor. This kills the three habits that make legacy
sheets brittle: dragging formulas down, helper columns, and hard-coded ranges. Write one
formula; it grows and shrinks with the data.

## When to use

Use when a report should recalculate and re-size itself. If you catch yourself "copy formula
down to the last row", "add a helper column", or "rebuild the PivotTable after new data" — stop
and reach for a spilling formula instead.

## Prerequisites

- **Version**: Dynamic arrays need Excel for Microsoft 365, Excel 2021, or later. GROUPBY /
  PIVOTBY / PERCENTOF need Microsoft 365 (rolled out 2024). Legacy Excel 2019 and earlier will
  show `#NAME?` — there is no back-port; use PivotTables there instead.
- **Source shape**: Cleanest results come from a structured Table (`Ctrl+T`) or a contiguous
  range with a header row.
- **Spill room**: The cells below/right of the anchor must be empty, or you get `#SPILL!`.

## Core building blocks

Reference a whole spill range with the anchor plus `#`, e.g. `=SUM(E2#)` sums whatever
`E2` spilled. This is how you chain formulas without knowing the size.

| Need | Formula | Note |
|------|---------|------|
| Distinct list | `=UNIQUE(Table[Region])` | add `TRUE` 3rd arg for once-only items |
| Filter rows | `=FILTER(Table[[Name]:[Sales]], Table[Sales]>1000, "none")` | 3rd arg = value if empty (avoids `#CALC!`) |
| Sort | `=SORT(FILTER(...), 2, -1)` | sort col 2 descending (`-1`) |
| Sort by other key | `=SORTBY(Table[Name], Table[Sales], -1)` | sort A by B without moving B |
| Number series | `=SEQUENCE(12,1,1,1)` | 12 rows, start 1, step 1 |
| Lookup (any direction) | `=XLOOKUP(G2, Table[SKU], Table[Price], "n/a")` | replaces VLOOKUP; 4th arg = not-found |
| Split text to columns | `=TEXTSPLIT(A2, ",")` | delimiter-based, spills across |
| Stack ranges | `=VSTACK(RegionA#, RegionB#)` / `=HSTACK(...)` | combine spills vertically/horizontally |

**FILTER with multiple conditions** — multiply Boolean arrays for AND, add for OR:

```
=FILTER(Table, (Table[Region]="EMEA")*(Table[Sales]>1000), "no rows")
```

**Top-N** — combine SORT + TAKE:

```
=TAKE(SORT(FILTER(Table[[Name]:[Sales]], Table[Sales]>0), 2, -1), 5)
```

## Recipe: distinct-count summary by category

Instead of a PivotTable, one formula per column that stays in sync:

```
Categories (spills down): =UNIQUE(Table[Category])
Totals   (next column):   =SUMIF(Table[Category], A2#, Table[Sales])
```

`A2#` feeds the entire spilled category list into `SUMIF`, so the totals column
auto-extends to match. Add a category to the source and both columns grow.

## Recipe: GROUPBY (grouped aggregation in one call)

`GROUPBY` collapses the two-formula pattern above into a single self-labelling block.
Syntax (grounded against Microsoft docs):

```
GROUPBY(row_fields, values, function, [field_headers], [total_depth], [sort_order], [filter_array], [field_relationship])
```

- `row_fields` — the column(s) to group by (row headers are generated for you).
- `values` — the column to aggregate.
- `function` — an aggregator: `SUM`, `AVERAGE`, `COUNT`, `MAX`, `MIN`, `PERCENTOF`, or any
  lambda (e.g. `LAMBDA(v, MEDIAN(v))`).
- `total_depth` — `0` none, `1` grand total, `2` grand + subtotals; negate (`-1`, `-2`) to
  put totals **at the top**.
- `sort_order` — index of the result column to sort on; negative = descending.
- `field_relationship` — `0` hierarchy (default), `1` table (independent columns).

```
Sales by region, descending, with grand total:
=GROUPBY(Table[Region], Table[Sales], SUM, , 1, -2)

Group by two fields, average, hierarchical:
=GROUPBY(Table[[Region]:[Rep]], Table[Sales], AVERAGE)
```

The block relabels and resizes when the source changes — no refresh, unlike a PivotTable.

## Recipe: PIVOTBY (rows x columns cross-tab)

Adds a column dimension. Same idea, two grouping axes:

```
PIVOTBY(row_fields, col_fields, values, function, [field_headers], [row_total_depth], [row_sort_order], [col_total_depth], [col_sort_order], [filter_array], [relative_to])
```

```
Total sales by product (rows) x year (cols):
=PIVOTBY(Table[Product], Table[Year], Table[Sales], SUM)

Share-of-row percentages instead of raw sums:
=PIVOTBY(Table[Product], Table[Year], Table[Sales], PERCENTOF, , , , , , , 1)
```

`relative_to` = `0` grand total, `1` row totals, `2` column totals — controls the base of
`PERCENTOF`.

## Verify

1. Type the formula in the **top-left anchor only** — never drag. Confirm a blue spill
   outline appears around the whole result.
2. Add a row to the source Table; the spill range should grow by one automatically. Delete a
   row; it should shrink. If it doesn't, the formula isn't referencing the Table/spill.
3. Reference the result elsewhere with `#` (e.g. `=ROWS(A2#)`) to prove downstream formulas
   track the live size.
4. Scan for error tokens: `#SPILL!`, `#CALC!`, `#NAME?`, `#N/A` — see Pitfalls.

## Pitfalls

- **`#SPILL!`** — something (a value, a merged cell, or another spill) blocks the output area.
  Clear the cells below/right of the anchor. Merged cells are a common culprit.
- **`#CALC!` from FILTER** — the filter matched zero rows. Always pass the 3rd
  `if_empty` argument (`"none"`, `0`, `""`).
- **`#NAME?`** — the function doesn't exist in this Excel version (GROUPBY/PIVOTBY/TEXTSPLIT
  need Microsoft 365) or a typo. There is no add-in fix; fall back to a PivotTable/SUMIF.
- **Don't wrap dynamic arrays in Tables** — putting a spilling formula inside a
  structured Table throws `#SPILL!`. Spill onto the open grid, then reference with `#`.
- **`@` implicit intersection** — if Excel silently prefixes your formula with `@`
  (e.g. `=@FILTER(...)`) it forces a single value. Delete the `@` to restore spilling.
- **Volatility of `#` refs** — deleting the anchor cell erases the whole spill and breaks
  every `#` reference; treat the anchor as load-bearing.
- **Absolute vs Table refs** — prefer `Table[Col]` over `$A$2:$A$999`; padded ranges reintroduce
  blank rows that `UNIQUE`/`GROUPBY` will surface as an empty group.
