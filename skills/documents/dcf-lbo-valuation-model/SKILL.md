---
name: dcf-lbo-valuation-model
category: documents
description: >
  Build a fully-linked DCF and LBO valuation in one Excel workbook — formulas only, zero hardcoded
  outputs — so every cell recalculates live when an assumption changes. Covers the unlevered FCFF
  bridge (EBIT → NOPAT → FCFF), a CAPM/WACC build, Gordon-growth and exit-multiple terminal value,
  enterprise-to-equity bridge and value per share, plus an LBO with sources & uses, a debt schedule
  with mandatory amort, and IRR/MOIC returns. Use when someone says "build me a DCF", "value this
  company", "LBO model", "what's the IRR", "MOIC", "WACC", "terminal value", "DCF in Excel", or
  "returns model" and wants a real linked spreadsheet, not a static number.
when_to_use:
  - "Build a discounted cash flow (DCF) model in Excel with live formulas, not baked-in numbers"
  - "Value a company and get enterprise value, equity value, and value per share"
  - "Build an LBO to compute sponsor IRR and MOIC over a holding period"
  - "Lay out a WACC build (CAPM cost of equity + after-tax cost of debt) that feeds the discounting"
  - "Compute terminal value both ways — Gordon perpetuity growth and exit EV/EBITDA multiple"
  - "Construct a debt schedule (opening → interest → mandatory amort → closing) for a leveraged deal"
when_not_to_use:
  - "Building the projected income statement / balance sheet / cash flow that feeds this — use three-statement-financial-model"
  - "Adding scenario switches or DATA TABLE sensitivity grids on top of a finished model — use excel-scenario-sensitivity"
  - "Auditing an existing model for broken links / hardcodes / #REF errors — use excel-model-audit"
  - "Generic 'open/edit any spreadsheet' work with no valuation content — use xlsx"
  - "Reusable custom calc logic via LAMBDA / dynamic arrays — use excel-lambda-functions or excel-dynamic-array-formulas"
keywords: [dcf, lbo, valuation, fcff, wacc, capm, terminal value, gordon growth, exit multiple, enterprise value, equity value, irr, moic, debt schedule, sources and uses, npv, xnpv, discount factor, ev/ebitda, openpyxl]
similar_to: [three-statement-financial-model, excel-scenario-sensitivity, excel-model-audit, excel-lambda-functions, xlsx]
inputs_needed:
  - Operating drivers — Year-0 revenue, growth %, EBIT margin, tax rate, D&A / CapEx / ΔNWC as % of revenue
  - Cost-of-capital inputs — risk-free rate, equity risk premium, levered beta, pre-tax cost of debt, target D/V
  - Terminal assumptions — perpetuity growth g OR exit EV/EBITDA multiple; net debt today; shares outstanding
  - LBO inputs (if doing the LBO) — entry EV/EBITDA multiple, entry leverage (Debt/EBITDA), fees %, amort %, holding period
produces: A .xlsx with linked Assumptions, DCF, and LBO sheets — every output is a formula referencing inputs; delivers EV, equity value, value/share, sponsor IRR and MOIC that recalculate live
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# DCF + LBO Valuation Model (linked, formulas-only)

Build a valuation the way a banker or PE analyst would: one **Assumptions** sheet that every other
cell points to, a **DCF** sheet that discounts unlevered free cash flow, and an **LBO** sheet that
levers the deal and computes returns. The non-negotiable rule: **outputs are formulas, never typed
numbers** — change an input and the whole model moves. This is the standard Macabacus / CFI house
style (blue = input, black = formula, green = cross-sheet link).

## When to use

Use this when the user wants an actual working valuation spreadsheet — "build me a DCF", "what's the
IRR on this LBO", "value this business". If they only need the *projections* that feed a valuation,
build those first with **three-statement-financial-model**, then link this on top.

## Prerequisites

- `python3` with `openpyxl` (`pip install openpyxl`) — writes formula strings into cells.
- openpyxl stores formulas but does **not** calculate them; Excel / LibreOffice / Google Sheets
  computes on open. So verify by opening, or replicate the math in Python (see **Verify**).
- Decide the two modelling choices up front: **terminal value method** (Gordon vs exit multiple) and
  whether cash flows are **year-end** (period `t = 1,2,3…`) or **mid-year** (`t = 0.5, 1.5…`).

## The finance (get these exactly right)

**Unlevered free cash flow (FCFF):**
```
NOPAT = EBIT × (1 − tax)
FCFF  = NOPAT + D&A − CapEx − ΔNWC          (ΔNWC increase is a cash outflow)
```

**Cost of capital:**
```
Cost of equity (CAPM) = Rf + β × ERP
After-tax cost of debt = Kd × (1 − tax)
WACC = (E/V) × Ke + (D/V) × Kd × (1 − tax)
```

**Terminal value** — pick one, show both:
```
Gordon growth:   TV = FCFF_final × (1 + g) / (WACC − g)      (requires WACC > g)
Exit multiple:   TV = EBITDA_final × exit EV/EBITDA
```
TV lands at the *end* of the final forecast year, so discount it with that year's discount factor.

**Bridge:** `EV = Σ PV(FCFF) + PV(TV)` → `Equity = EV − net debt` → `Per share = Equity / shares`.

**LBO returns:**
```
Entry EV = entry EBITDA × entry multiple ; Uses = Entry EV + fees
Sources  = new debt + sponsor equity (equity is the plug)
Exit equity = exit EBITDA × exit multiple − exit net debt
MOIC = exit equity / sponsor equity
IRR  = MOIC^(1/years) − 1   (single in/out)   OR   =IRR(cashflow_row)  (staged flows)
```

## Recipe A — generate the whole workbook (openpyxl)

`scripts/build_model.py` writes all three linked sheets in one shot. It is smoke-tested: 102 formula
cells, zero `#REF!`, and reproduces WACC 8.4% / EV $2,925m / $25.25 per share and a 2.46x MOIC /
19.7% IRR on its default inputs.

```bash
python3 scripts/build_model.py my_valuation.xlsx
```

Then edit any **blue** cell on the Assumptions sheet in Excel and every downstream number updates.
Read the script for the full cell map; the load-bearing patterns are below.

## Recipe B — the formulas that matter (drop into any layout)

Assume the Assumptions sheet holds each driver in column C, and the DCF forecast runs across columns
`C:G` (Years 1–5), with Year 0 in column B.

**FCFF row (per year column, here G = Year 5):**
```excel
Revenue   =F5*(1+Assumptions!$C$5)              ' prior year × (1 + growth)
EBIT      =G4*Assumptions!$C$6                   ' revenue × EBIT margin
CashTax   =-G5*Assumptions!$C$7                  ' NOPAT haircut (negative)
D&A       =G4*Assumptions!$C$8                   ' add back (positive)
CapEx     =-G4*Assumptions!$C$9                  ' outflow (negative)
ΔNWC      =-(G4-F4)*Assumptions!$C$10            ' outflow on revenue growth
FCFF      =G5+G6+G7+G8+G9                         ' signed rows just sum
```

**WACC and discounting:**
```excel
Ke     =Assumptions!$C$12+Assumptions!$C$14*Assumptions!$C$13     ' Rf + β·ERP
Kd_at  =Assumptions!$C$15*(1-Assumptions!$C$7)                    ' Kd·(1−tax)
WACC   =(1-Assumptions!$C$16)*Ke+Assumptions!$C$16*Kd_at
DF     =1/(1+$B$16)^G18                          ' G18 = period t (1..5); mid-year: t-0.5
PV     =G10*G19                                  ' FCFF × discount factor
```

**Terminal value + bridge:**
```excel
TV_gordon =G10*(1+Assumptions!$C$17)/($B$16-Assumptions!$C$17)
TV_exit   =G4*Assumptions!$C$11*Assumptions!$C$18            ' EBITDA_final × exit mult
PV_TV     =B25*G19                                          ' TV × final-year DF
EV        =SUM(C20:G20)+B26                                 ' ΣPV(FCFF) + PV(TV)
Equity    =EV-Assumptions!$C$19                             ' minus net debt
PerShare  =Equity/Assumptions!$C$20
```
> Do **not** use bare `=NPV(rate,range)` for FCFF — Excel's `NPV` discounts the *first* value by one
> full period. Discount explicitly with a discount-factor row (as above), or use `XNPV` with dates.

**LBO debt schedule (per year, prior-year closing feeds next opening):**
```excel
Opening  =PrevYearClosing            ' Year 1 opening = new debt raised
Interest =Opening*Assumptions!$C$15
Amort    =MIN(Opening, $B$8*Assumptions!$C$21)   ' can't repay more than outstanding
Closing  =Opening-Amort
```

**Returns:**
```excel
ExitEquity =ExitEBITDA*Assumptions!$C$18 - FinalClosingDebt
MOIC       =ExitEquity/SponsorEquity          ' format 0.0"x"
IRR        =(ExitEquity/SponsorEquity)^(1/Assumptions!$C$22)-1
IRR_staged =IRR(B29:F29)                        ' row: -equity, 0, 0, 0, +exit equity
```

## Verify

- **No dead links:** open in Excel/Sheets and confirm no `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`.
  Programmatic scan: load with openpyxl and assert no cell string contains `#REF`.
- **Recalc is live:** change Year-0 revenue on Assumptions — EV, per-share, IRR and MOIC must all
  move. If a number is frozen, it was hardcoded — replace it with a formula.
- **Sanity bands:** WACC typically 6–12%; DCF implied EV/EBITDA in a believable range; LBO sponsor
  IRR usually 15–30% and MOIC 2–3x over 5 years. Wild numbers mean a sign or reference error.
- **Cross-check the math in Python** (openpyxl won't calc): replicate FCFF, WACC, TV, EV and MOIC in
  a short script and compare to what Excel shows — they must match to the cent.
- **WACC > g:** if the Gordon TV denominator `(WACC − g)` is ≤ 0 the model is nonsensical; flag it.

## Pitfalls

- **Hardcoding outputs.** The cardinal sin. Every EV, IRR, and TV must be a formula. If you paste a
  number, the model is dead the moment an input changes.
- **NPV off-by-one.** Excel `NPV` assumes the first cash flow is one period away. Use an explicit
  discount-factor row or `XNPV`; otherwise every valuation is silently ~1 period too low.
- **Terminal value dominance.** PV(TV) is often 60–80% of EV. Show both methods and pressure-test g
  and the exit multiple — a 0.5% move in g can swing value 10%+.
- **ΔNWC sign flip.** A working-capital *increase* consumes cash (negative in FCFF). Getting the sign
  backwards inflates free cash flow.
- **Circularity (interest ↔ cash).** Full cash-sweep LBOs create a circular reference (interest
  depends on debt, debt paydown depends on post-interest cash). This skill uses *mandatory* amort to
  stay circularity-free. If you add a sweep, enable iterative calculation in Excel and add a switch.
- **Mid-year convention.** If you claim mid-year discounting, use `t = 0.5, 1.5, …` for the FCFF
  factors AND discount the TV at the final *year-end* factor (TV occurs at period end, not mid-year).
- **Levered vs unlevered mix-up.** DCF discounts *unlevered* FCFF at WACC. Don't subtract interest in
  the FCFF build — leverage enters only through WACC and the LBO debt schedule.
