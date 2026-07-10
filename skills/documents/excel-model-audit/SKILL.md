---
name: excel-model-audit
category: documents
description: >
  Error-proof and stress-test a spreadsheet financial model against FAST and ICAEW
  standards. Use to hunt hardcodes buried in formulas, #REF!/#DIV0 errors, inconsistent
  formulas across a row, external links and volatile functions; to apply IFERROR/IFNA
  discipline; to trace precedents/dependents; and to restructure inputs-workings-outputs
  so the model is Flexible, Appropriate, Structured & Transparent. Trigger on "audit my
  model", "check this spreadsheet for errors", "why does this cell break", "model review".
when_to_use:
  - Reviewing or handing over a financial model (three-statement, DCF, LBO, budget) before it goes live
  - A model returns #REF!, #DIV/0!, #VALUE! or circular-reference errors and you need the root cause
  - You suspect hardcoded numbers, inconsistent row formulas, or hidden links to other workbooks
  - Enforcing FAST / ICAEW structure (separate inputs, workings, outputs; consistent time series)
  - Adding IFERROR/IFNA guards and integrity checks (balance-sheet balances, flag = 0/1) before sign-off
when_not_to_use:
  - Building a new model from scratch — use three-statement-financial-model or dcf-lbo-valuation-model
  - Designing scenario/sensitivity switches — use excel-scenario-sensitivity
  - Writing dynamic-array or LAMBDA logic — use excel-dynamic-array-formulas or excel-lambda-functions
  - General spreadsheet read/write/reshape with no audit intent — use xlsx
keywords:
  - excel
  - model audit
  - fast standard
  - icaew
  - iferror
  - trace precedents
  - hardcode
  - circular reference
  - integrity check
  - formula consistency
  - financial model
  - error handling
  - openpyxl
  - spreadsheet review
similar_to:
  - three-statement-financial-model
  - dcf-lbo-valuation-model
  - excel-scenario-sensitivity
  - excel-dynamic-array-formulas
  - xlsx
inputs_needed: An .xlsx workbook (path) plus which sheets are model vs source; access to Excel/LibreOffice for interactive tracing is optional.
produces: A ranked list of integrity findings (critical→low), fixed formulas with IFERROR/flag guards, and a FAST/ICAEW-structured layout recommendation.
status: stable
owner: seb.duffy
updated: 2026-07-09
---

# Excel Model Audit

Systematically error-proof a formula model. Grounded in the **FAST Standard**
(Flexible, Appropriate, Structured, Transparent — fast-standard.org) and **ICAEW's
Twenty Principles for Good Spreadsheet Practice** (2024 edition). Two layers: a
static `openpyxl` auditor that scans the file offline, and an interactive tracing
checklist you run inside Excel.

## When to use

Reach for this before any model is signed off, handed over, or blamed. If a cell
shows `#REF!`, if numbers are typed into the middle of formulas, or if you can't
trust that row 40 does the same thing across every period — audit first, fix second.

## Prerequisites

- `python3 -m pip install --user openpyxl` (tested with openpyxl 3.1.5 on Python 3.9).
- The workbook saved as `.xlsx` (not `.xls`). Keep an untouched backup — never audit-and-overwrite the only copy.
- Optional but ideal: Excel or LibreOffice open, to recalc the file (see Pitfall 1) and to trace visually.

## Recipe 1 — Static scan (offline, no Excel)

Run the bundled auditor. It flags the six defects that break models most often.

```bash
python3 scripts/audit_model.py path/to/model.xlsx        # human-readable, ranked
python3 scripts/audit_model.py path/to/model.xlsx --json # machine-readable
```

What each code means and the FAST/ICAEW rule it enforces:

| Code | Severity | Rule broken |
|------|----------|-------------|
| `ERROR` | critical | Cached value is `#REF!/#DIV0/#VALUE!/#N/A` — a live break (ICAEW P17: test/protect). |
| `HARDCODE` | high | A number is buried in a formula instead of a labelled blue input (FAST: no constants in calcs; ICAEW P10: separate inputs). |
| `INCONSISTENT_ROW` | high | One cell in a row does a *different* calc from its neighbours — the classic copy-drift bug (FAST: one consistent formula across the row). |
| `EXTERNAL_LINK` | high | Formula points at `[Other.xlsx]` — a fragile dependency that breaks on the recipient's machine. |
| `DEEP_NEST` | medium | 4+ nested `IF` — replace with flag rows (0/1) or `IFS`/`SWITCH` (FAST: transparent, short formulas). |
| `VOLATILE` | low | `OFFSET/INDIRECT/NOW/TODAY/RAND` recalc on every keystroke and hide precedent trails. |

The exit code is `1` if any critical/high finding exists — wire it into CI or a pre-commit gate.

## Recipe 2 — Interactive tracing inside Excel

For each critical/high finding, confirm the root cause with these built-ins:

- **Show all formulas at once:** `Ctrl` + `` ` `` (grave). Reveals hardcodes and drift down a column instantly. Press again to revert.
- **Trace Precedents / Dependents:** Formulas ▸ Trace Precedents (`Ctrl`+`[` jumps to them) / Trace Dependents (`Ctrl`+`]`). Arrows expose where a `#REF!` originates.
- **Evaluate Formula:** Formulas ▸ Evaluate Formula — step through a nested expression one operation at a time to see exactly where it turns into an error.
- **Find every hardcode:** `Ctrl`+`G` ▸ Special ▸ *Constants* (untick Text) highlights every typed number in the calc block. In a clean FAST model, the workings area contains **none**.
- **Find every error cell:** `Ctrl`+`G` ▸ Special ▸ *Formulas* ▸ *Errors*.
- **Circular references:** Formulas ▸ Error Checking ▸ Circular References lists them; the status bar shows the first cell. Genuine circularities (interest-on-debt) need iterative calc enabled *deliberately*, not by accident.
- **Watch Window** (Formulas ▸ Watch Window): pin your integrity checks and key outputs, then watch them as you edit far-away inputs.

## Recipe 3 — Add error & integrity discipline

Fix, don't just find. Apply guards **at the source of the error, not the outer wrapper** — a blanket `IFERROR` around a whole formula hides the next bug too.

```excel
# Guard only the division that can be zero-denominator:
=Sales / IFERROR(Volume, 0)              # WRONG: silently 0, masks a real gap
=IF(Volume=0, 0, Sales/Volume)           # RIGHT: intent explicit
=IFERROR(Sales/Volume, 0)                # OK when 0 is the true business answer

# Prefer IFNA over IFERROR for lookups — it catches "not found" but still
# lets a genuine #REF!/#DIV0 surface loudly:
=IFNA(XLOOKUP(id, ids, vals), "unmatched")

# Sum a column that may contain errors without them poisoning the total:
=AGGREGATE(9, 6, C5:C40)                 # 9=SUM, 6=ignore errors
```

**Integrity checks** — a FAST model carries its own alarms. Add a checks block and keep every cell TRUE/0:

```excel
Balance check      =ROUND(TotalAssets-(TotalLiabs+Equity), 2)   # must be 0
Cash tie-out       =ROUND(CF_ending - BS_cash, 2)               # must be 0
Flow flag          =IF(SUM(Checks_range)=0, "OK", "BREAK")      # single traffic light
```

## Recipe 4 — Restructure to FAST / ICAEW

If the scan shows structural rot, refactor before patching:

1. **Separate inputs, workings, outputs** (ICAEW P10). Inputs on their own sheet/block, coloured **blue**; formulas **black**; links to other sheets **green**; external/warning cells **red**. Never mix a typed input into a calculation cell.
2. **One direction of flow** — calculations read left-to-right, top-to-bottom; no formula points *down* or *right* to a value computed later (FAST: Structured).
3. **Consistent time series** — the same column is the same period on *every* sheet, so a single formula copies clean across the row.
4. **Corkscrew / BASE for every balance** — Brought-forward + Additions − Subtractions = Carried-forward. Never overwrite a running balance in place.
5. **Short, transparent formulas** — if you can't read it aloud, split it into flag rows and intermediate steps (FAST: Transparent; ICAEW P16).
6. **An 'About' sheet** (ICAEW P7): purpose, author, version, colour key, list of inputs and integrity checks.

## Verify

- `python3 scripts/audit_model.py model.xlsx` exits `0` (no critical/high) — or every remaining finding is a documented, intentional exception.
- `Ctrl`+`G` ▸ Special ▸ Constants finds **zero** typed numbers in the workings area.
- Every cell in the checks block reads 0 / OK, including after you flex a key input up and down.
- Trace Precedents on each output terminates at labelled blue inputs — no dead ends, no external `[workbook]` links.

## Pitfalls

1. **openpyxl only sees *cached* values.** A file never opened in Excel (or freshly written by a script) has no cached results, so the `ERROR` check can miss `#DIV/0!` until you open, recalc (`Ctrl`+`Alt`+`F9`) and save the file once. Always recalc-and-save before the static scan, and still run Recipe 2's error-check in-app.
2. **`IFERROR` is a cover-up, not a fix.** Wrapping a formula silences the *next* bug too. Guard the narrowest failing sub-expression, and prefer `IFNA` for lookups so structural errors stay loud.
3. **Benign numbers aren't hardcodes.** `0`, `1`, `12`, `365`, `100` (unit/period constants) are allowed inside formulas — the auditor's `BENIGN` set skips them. A tax rate or growth % typed into a formula is *not* benign; move it to a blue input.
4. **Inconsistent-row false positives at block edges.** The first/last cell of a series legitimately differs (an opening hardcode, a total). Read `INCONSISTENT_ROW` findings in context before "fixing" a deliberate anchor.
5. **Not every circular reference is a bug.** Interest-on-average-debt is genuinely circular and needs iterative calc *on purpose*. Distinguish designed circularity from an accidental one — the accidental kind usually shows a stray `#REF!` or a 0 where a number belongs.
6. **`.xls` and password-protected files won't parse.** Re-save as unprotected `.xlsx` first.
