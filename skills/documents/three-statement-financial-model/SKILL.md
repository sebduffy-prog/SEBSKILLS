---
name: three-statement-financial-model
category: documents
description: >
  Build a fully-linked three-statement financial model (income statement, balance sheet,
  cash flow) in Excel with FORMULAS ONLY — every forecast cell references a driver or
  another statement line, never a hard-coded number. Use when asked to build a 3-statement
  model, integrated financial model, forecast/projection workbook, or operating model, or
  when a balance sheet won't balance, interest is circular, or a cash-flow bridge must tie
  out. Covers driver schedules, working-capital days, revolver cash-sweep, circular
  interest via iterative calc, and a balance-check that proves zero.
when_to_use:
  - Building an integrated 3-statement model or forecast/projection workbook from drivers
  - A balance sheet won't balance and you need the accounting identity that forces it to zero
  - Interest expense is circular (interest -> debt -> cash -> interest) and Excel throws a circular-ref warning
  - Wiring a cash-flow statement that ties opening cash to closing cash and reconciles to the balance sheet
  - Auditing whether a model is truly formula-driven vs. plugged with hard-coded outputs
when_not_to_use:
  - Pure DCF/LBO valuation, WACC, IRR, or returns waterfalls — use dcf-lbo-valuation-model
  - Scenario/sensitivity tables, data tables, or tornado charts on an existing model — use excel-scenario-sensitivity
  - Auditing/tracing an inherited workbook for errors and precedents — use excel-model-audit
  - A summary KPI/output dashboard rather than the statements themselves — use excel-kpi-dashboard-formulas
keywords: [three-statement-model, financial-model, income-statement, balance-sheet, cash-flow, integrated-model, circularity, revolver, working-capital, iterative-calculation, forecast, openpyxl, excel, balance-check, driver-schedule]
similar_to: [dcf-lbo-valuation-model, excel-scenario-sensitivity, excel-model-audit, excel-kpi-dashboard-formulas]
inputs_needed: Year-0 opening balances (revenue, PPE, cash, AR/inventory/AP, debt) and forecast drivers (growth %, margins, working-capital days, tax rate, interest rate, capex %, dividend payout). Sensible defaults are provided.
produces: A .xlsx workbook with a fully-linked IS/BS/CF, a driver block, iterative calc enabled, and a Check row that reads 0.0 in every column.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Three-Statement Financial Model (formulas only)

Build IS + BS + CF where the three statements are **wired together**, not typed in. The
balance sheet balances *by construction* (accounting identity below), and the `Check` row
proves it reads zero. Interest is genuinely circular and resolves via Excel iterative calc.

## When to use

Reach for this whenever the deliverable is the *integrated statements* themselves: a
forecast built from drivers, a broken balance sheet, or a circular-interest warning. For
valuation on top of a model use `dcf-lbo-valuation-model`; for sensitivity use
`excel-scenario-sensitivity`.

## Prerequisites

- `python3` (macOS system 3.9 is fine) + `openpyxl` (`python3 -c "import openpyxl"`).
- No Excel needed to *build*; you need Excel/LibreOffice/Numbers to *recalculate* (openpyxl
  writes formulas but does not evaluate them).

## The three rules that make it work

1. **One driver block, referenced everywhere.** Growth, margins, days, rates live in cells
   in one place. Every statement line is `=<other cell> * <driver cell>`. No output is ever
   a literal — that is what "formulas only" means and what `excel-model-audit` checks for.
2. **Cash and debt are the plugs; everything else is defined.** AR/inventory/AP come from
   working-capital days; PPE rolls opening − depreciation + capex; equity rolls opening +
   net income − dividends. **Cash comes from the cash-flow statement**, and the **revolver**
   absorbs any shortfall below a minimum-cash floor. Nothing else is free.
3. **Let the identity balance it.** Because cash is the CF-derived residual and equity rolls
   NI − dividends, the balance sheet balances automatically:

   ```
   ΔAssets = ΔCash + ΔAR + ΔInv + ΔPPE
           = (NI + D&A − ΔAR − ΔInv + ΔAP − Capex + ΔDebt − Div) + ΔAR + ΔInv + (Capex − D&A)
           = NI + ΔAP + ΔDebt − Div
   ΔL&E    = ΔAP + ΔDebt + (NI − Div)  =  NI + ΔAP + ΔDebt − Div   ✅ equal
   ```

   So if **year 0 balances**, every forecast year balances. The `Check` row is your proof,
   not your plug — if it isn't zero you have a formula error, not a missing balancing entry.

## The interest circularity (and how to survive it)

Interest is charged on **average debt** `=(opening + closing)/2 * rate`. Closing debt = the
revolver, which is drawn to cover cash shortfalls; cash depends on interest; interest depends
on debt → **circular**. Two things make this safe:

- **Enable iterative calculation** so Excel converges instead of erroring. In openpyxl:
  ```python
  wb.calculation.iterate = True          # Excel: File ▸ Options ▸ Formulas ▸ Enable iterative calc
  wb.calculation.iterateCount = 100
  wb.calculation.iterateDelta = 1e-6
  wb.calculation.fullCalcOnLoad = True
  ```
- **A CIRC switch cell** (`1`=on, `0`=break). Interest = `=CIRC * avg_debt * rate`. Set it to
  `0` to zero-out interest and instantly break every circular reference when a model is
  spinning or shows `#VALUE!`; flip back to `1` once it's stable. This is the standard
  circularity breaker taught by CFI — never delete the links, just gate them.

## Recipe: build the model

`scripts/build_model.py` writes the whole thing. Run it, open in Excel, confirm the check.

```bash
python3 scripts/build_model.py my_model.xlsx
```

It lays out one `Model` sheet: driver block, then IS, BS, CF, with column B = Year 0
(opening) and C–G = forecast years 1–5. Every forecast cell is a formula. The key lines:

```
Revenue    C = =B<rev>*(1+$B$<growth>)
COGS       C = =-C<rev>*$B$<cogs%>
D&A        C = =-B<netPPE>*$B$<dep%>              # depreciate OPENING PPE
Interest   C = =-$B$<CIRC>*((B<debt>+C<debt>)/2)*$B$<rate>   # circular, gated by CIRC
Net PPE    C = =B<netPPE>+C<D&A>+C<rev>*$B$<capex%>   # +D&A (it's negative) − i.e. minus dep
Cash       C = =C<closingCash>                    # cash is the CF plug
AR         C = =C<rev>*$B$<DSO>/365
Inventory  C = =-C<COGS>*$B$<DIO>/365
AP         C = =-C<COGS>*$B$<DPO>/365
Equity     C = =B<equity>+C<NI>+C<dividends>      # dividends stored negative
Revolver   C = =MAX(minc-avail,0) - MIN(MAX(avail-minc,0),B<debt>)   # draw / sweep
Check      C = =C<totalAssets>-C<totalL&E>        # must read 0.0
```

**Sign convention** (pick one and hold it): expenses, capex, dividends and revolver repayments
are stored **negative** so every subtotal is a `SUM(...)` or a `+`. This is why Net PPE adds
`C<D&A>` (a negative) rather than subtracting a positive — mixing conventions is the #1 cause
of a model that won't tie.

## Verify

1. **Build runs clean:** `python3 scripts/build_model.py verify.xlsx` prints `saved verify.xlsx`.
2. **Iterative calc persisted:**
   ```bash
   python3 -c "import openpyxl;print(openpyxl.load_workbook('verify.xlsx').calculation.iterate)"  # True
   ```
3. **The check is zero.** Open in Excel (or LibreOffice `--calc`) and read the `Check (A-L&E)`
   row — every forecast column must show `0.0` (or `< 1e-6`). The build ships a verified
   parameter set whose check is 0 to machine precision in all five years with interest ON.
4. **It's truly formula-only:** every populated forecast cell starts with `=`. Spot-check:
   ```bash
   python3 -c "import openpyxl;ws=openpyxl.load_workbook('verify.xlsx')['Model'];
   print(all(str(ws['C'+str(r)].value).startswith('=') for r in range(19,25)))"  # True
   ```

## Pitfalls

- **openpyxl never computes.** After building, values are `None` until Excel recalculates.
  Don't assert numbers from Python — assert that cells contain the right *formulas*, then open
  in a spreadsheet app to read results.
- **Iterative calc off = `#REF!`/circular warning.** If a colleague opens the file with
  iterative calc disabled in their Excel, interest breaks. Ship it with `fullCalcOnLoad` and
  tell them to enable it, or hand them the CIRC=0 version.
- **Depreciate opening PPE, not closing.** Charging depreciation on the same-year PPE (which
  already includes this year's capex) creates its own mini-circularity and overstates D&A.
- **Year 0 must balance first.** The identity only propagates a *balanced* opening. The script
  makes equity the year-0 plug so `TA = TL&E` before any forecast; never skip that.
- **Don't add a manual "balancing figure" to force the check to zero.** That hides the real
  error. A non-zero check means a broken link — trace it with `excel-model-audit`.
- **Mixed sign conventions** silently break subtotals. If EBITDA looks too high, check whether
  a cost line is stored positive. Keep costs negative end to end.
- **Revolver can't repay more than it owes.** The `MIN(..., opening_debt)` clamp is essential;
  without it a cash-rich year drives debt negative (a phantom asset).
